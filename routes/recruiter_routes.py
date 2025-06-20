from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, Recruiter, Job, Application, Candidate
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime

# Create Blueprint
recruiter = Blueprint('recruiter', __name__, url_prefix='/recruiter')

def recruiter_login_required(f):
    """Decorator to require recruiter login"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('main.login'))
        
        if session.get('user_type') != 'recruiter':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@recruiter.route('/register', methods=['GET', 'POST'])
def register():
    """Recruiter registration route"""
    errors = {}
    
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        company_name = request.form.get('company_name', '').strip()
        company_description = request.form.get('company_description', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        company_location = request.form.get('company_location', '').strip()
        website_url = request.form.get('website_url', '').strip()
        
        # Validate form data
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors['email'] = "Please enter a valid email address."
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            errors['email'] = "This email is already registered. Please use a different email or login."
        
        if not password or len(password) < 8:
            errors['password'] = "Password must be at least 8 characters long."
        
        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."
        
        if not company_name:
            errors['company_name'] = "Company name is required."
        
        # If no errors, create the user
        if not errors:
            try:
                # Create user with explicit hashing method
                password_hash = generate_password_hash(password, method='pbkdf2:sha256')
                print(f"Registration - Generated password hash for {email}: {password_hash}")
                
                new_user = User(
                    email=email,
                    password_hash=password_hash,
                    user_type='recruiter'
                )
                db.session.add(new_user)
                db.session.flush()  # Get the user_id without committing
                
                # Create recruiter profile
                new_recruiter = Recruiter(
                    user_id=new_user.user_id,
                    company_name=company_name,
                    company_description=company_description if company_description else None,
                    contact_person=contact_person if contact_person else None,
                    company_location=company_location if company_location else None,
                    website_url=website_url if website_url else None,
                    reputation_score=0.0  # Default reputation score
                )
                db.session.add(new_recruiter)
                db.session.commit()
                
                # Verify the password immediately after creation
                verification = check_password_hash(password_hash, password)
                print(f"Registration - Password verification: {verification}")
                
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('main.login'))
                
            except Exception as e:
                db.session.rollback()
                print(f"Registration error: {str(e)}")
                flash(f'An error occurred during registration. Please try again.', 'error')
    
    return render_template('recruiter/register.html', errors=errors)

@recruiter.route('/dashboard')
@recruiter_login_required
def dashboard():
    """Recruiter dashboard route"""
    recruiter_id = session.get('recruiter_id')
    recruiter = Recruiter.query.get(recruiter_id)
    
    # Get dashboard statistics
    try:
        stats = {
            'total_jobs': Job.query.filter_by(recruiter_id=recruiter_id).count(),
            'active_jobs': Job.query.filter_by(recruiter_id=recruiter_id, status='open', is_approved=True).count(),
            'pending_jobs': Job.query.filter_by(recruiter_id=recruiter_id, is_approved=False).count(),
            'total_applications': db.session.query(Application).join(Job).filter(Job.recruiter_id == recruiter_id).count()
        }
        
        # Get recent jobs
        recent_jobs = Job.query.filter_by(recruiter_id=recruiter_id)\
                              .order_by(Job.posted_date.desc())\
                              .limit(5).all()
        
        # Get recent applications
        recent_applications = db.session.query(Application).join(Job)\
                                       .filter(Job.recruiter_id == recruiter_id)\
                                       .order_by(Application.application_date.desc())\
                                       .limit(5).all()
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        stats = {'total_jobs': 0, 'active_jobs': 0, 'pending_jobs': 0, 'total_applications': 0}
        recent_jobs = []
        recent_applications = []
    
    return render_template('recruiter/dashboard.html', 
                         recruiter=recruiter, 
                         stats=stats,
                         recent_jobs=recent_jobs,
                         recent_applications=recent_applications)

@recruiter.route('/profile')
@recruiter_login_required
def profile():
    """Recruiter profile route"""
    recruiter_id = session.get('recruiter_id')
    recruiter = Recruiter.query.get(recruiter_id)
    return render_template('recruiter/profile.html', recruiter=recruiter)

@recruiter.route('/jobs')
@recruiter_login_required
def jobs():
    """Recruiter jobs management route"""
    recruiter_id = session.get('recruiter_id')
    try:
        jobs = Job.query.filter_by(recruiter_id=recruiter_id)\
                       .order_by(Job.posted_date.desc()).all()
    except Exception as e:
        print(f"Jobs error: {str(e)}")
        jobs = []
    
    return render_template('recruiter/jobs.html', jobs=jobs)

@recruiter.route('/jobs/create', methods=['GET', 'POST'])
@recruiter_login_required
def create_job():
    """Create job posting route"""
    errors = {}
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        salary_range = request.form.get('salary_range', '').strip()
        skills_required = request.form.get('skills_required', '').strip()
        required_experience = request.form.get('required_experience', '')
        
        # Validate form data
        if not title:
            errors['title'] = "Job title is required."
        elif len(title) < 3:
            errors['title'] = "Job title must be at least 3 characters long."
        elif len(title) > 100:
            errors['title'] = "Job title must be less than 100 characters."
        
        if not description:
            errors['description'] = "Job description is required."
        elif len(description) < 5:
            errors['description'] = "Job description must be at least 50 characters long."
        elif len(description) > 5000:
            errors['description'] = "Job description must be less than 5000 characters."
        
        if not location:
            errors['location'] = "Location is required."
        elif len(location) > 100:
            errors['location'] = "Location must be less than 100 characters."
        
        if salary_range and len(salary_range) > 50:
            errors['salary_range'] = "Salary range must be less than 50 characters."
        
        if not skills_required:
            errors['skills_required'] = "At least one skill is required."
        elif len(skills_required) > 500:
            errors['skills_required'] = "Skills list is too long. Please keep it under 500 characters."
        
        if not required_experience:
            errors['required_experience'] = "Required experience level is required."
        else:
            try:
                required_experience = int(required_experience)
                if required_experience < 0 or required_experience > 50:
                    errors['required_experience'] = "Experience must be between 0 and 50 years."
            except ValueError:
                errors['required_experience'] = "Invalid experience value."
        
        # If no errors, create the job
        if not errors:
            try:
                recruiter_id = session.get('recruiter_id')
                
                new_job = Job(
                    recruiter_id=recruiter_id,
                    title=title,
                    description=description,
                    location=location,
                    salary_range=salary_range if salary_range else None,
                    skills_required=skills_required,
                    required_experience=required_experience,
                    status='open',
                    is_approved=True,  # Jobs need admin approval
                    posted_date=datetime.utcnow()
                )
                db.session.add(new_job)
                db.session.commit()
                
                flash('Job posted successfully! .', 'success')
                return redirect(url_for('recruiter.jobs'))
                
            except Exception as e:
                db.session.rollback()
                print(f"Job creation error: {str(e)}")
                flash('An error occurred while posting the job. Please try again.', 'error')
    
    return render_template('recruiter/create_job.html', errors=errors)

@recruiter.route('/jobs/edit/<int:job_id>', methods=['GET', 'POST'])
@recruiter_login_required
def edit_job(job_id):
    """Edit job posting route"""
    recruiter_id = session.get('recruiter_id')
    job = Job.query.filter_by(job_id=job_id, recruiter_id=recruiter_id).first_or_404()
    errors = {}
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        salary_range = request.form.get('salary_range', '').strip()
        skills_required = request.form.get('skills_required', '').strip()
        required_experience = request.form.get('required_experience', '')
        
        # Validate form data (same validation as create)
        if not title:
            errors['title'] = "Job title is required."
        elif len(title) < 3:
            errors['title'] = "Job title must be at least 3 characters long."
        elif len(title) > 100:
            errors['title'] = "Job title must be less than 100 characters."
        
        if not description:
            errors['description'] = "Job description is required."
        elif len(description) < 50:
            errors['description'] = "Job description must be at least 50 characters long."
        elif len(description) > 5000:
            errors['description'] = "Job description must be less than 5000 characters."
        
        if not location:
            errors['location'] = "Location is required."
        elif len(location) > 100:
            errors['location'] = "Location must be less than 100 characters."
        
        if salary_range and len(salary_range) > 50:
            errors['salary_range'] = "Salary range must be less than 50 characters."
        
        if not skills_required:
            errors['skills_required'] = "At least one skill is required."
        elif len(skills_required) > 500:
            errors['skills_required'] = "Skills list is too long. Please keep it under 500 characters."
        
        if not required_experience:
            errors['required_experience'] = "Required experience level is required."
        else:
            try:
                required_experience = int(required_experience)
                if required_experience < 0 or required_experience > 50:
                    errors['required_experience'] = "Experience must be between 0 and 50 years."
            except ValueError:
                errors['required_experience'] = "Invalid experience value."
        
        # If no errors, update the job
        if not errors:
            try:
                job.title = title
                job.description = description
                job.location = location
                job.salary_range = salary_range if salary_range else None
                job.skills_required = skills_required
                job.required_experience = required_experience
                
                # If job was previously approved and now edited, it needs re-approval
                if job.is_approved:
                    job.is_approved = False
                    job.status = 'pending'
                    flash('Job updated successfully! Since you made changes, it will need admin re-approval.', 'info')
                else:
                    flash('Job updated successfully!', 'success')
                
                db.session.commit()
                return redirect(url_for('recruiter.jobs'))
                
            except Exception as e:
                db.session.rollback()
                print(f"Job update error: {str(e)}")
                flash('An error occurred while updating the job. Please try again.', 'error')
    
    return render_template('recruiter/edit_job.html', job=job, errors=errors)

@recruiter.route('/jobs/delete/<int:job_id>', methods=['POST'])
@recruiter_login_required
def delete_job(job_id):
    """Delete job posting route"""
    recruiter_id = session.get('recruiter_id')
    job = Job.query.filter_by(job_id=job_id, recruiter_id=recruiter_id).first_or_404()
    
    try:
        # Check if job has applications
        application_count = Application.query.filter_by(job_id=job_id).count()
        
        if application_count > 0:
            flash(f'Cannot delete job "{job.title}" because it has {application_count} application(s). You can close it instead.', 'error')
        else:
            db.session.delete(job)
            db.session.commit()
            flash(f'Job "{job.title}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Job deletion error: {str(e)}")
        flash('An error occurred while deleting the job.', 'error')
    
    return redirect(url_for('recruiter.jobs'))

@recruiter.route('/jobs/toggle-status/<int:job_id>', methods=['POST'])
@recruiter_login_required
def toggle_job_status(job_id):
    """Toggle job status between open and closed"""
    recruiter_id = session.get('recruiter_id')
    job = Job.query.filter_by(job_id=job_id, recruiter_id=recruiter_id).first_or_404()
    
    try:
        if job.status == 'open':
            job.status = 'closed'
            flash(f'Job "{job.title}" has been closed.', 'info')
        else:
            job.status = 'open'
            flash(f'Job "{job.title}" has been reopened.', 'success')
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Job status toggle error: {str(e)}")
        flash('An error occurred while updating the job status.', 'error')
    
    return redirect(url_for('recruiter.jobs'))

@recruiter.route('/applications')
@recruiter_login_required
def applications():
    """View all applications route"""
    recruiter_id = session.get('recruiter_id')
    try:
        # Get all applications for this recruiter's jobs
        applications = db.session.query(Application).join(Job)\
                                .filter(Job.recruiter_id == recruiter_id)\
                                .order_by(Application.application_date.desc()).all()
        
        # Get all jobs for filter dropdown
        jobs = Job.query.filter_by(recruiter_id=recruiter_id).all()
        
    except Exception as e:
        print(f"Applications error: {str(e)}")
        applications = []
        jobs = []
    
    return render_template('recruiter/applications.html', applications=applications, jobs=jobs)

@recruiter.route('/applications/<int:job_id>')
@recruiter_login_required
def job_applications(job_id):
    """View applications for a specific job"""
    recruiter_id = session.get('recruiter_id')
    job = Job.query.filter_by(job_id=job_id, recruiter_id=recruiter_id).first_or_404()
    
    try:
        applications = Application.query.filter_by(job_id=job_id)\
                                      .order_by(Application.application_date.desc()).all()
    except Exception as e:
        print(f"Job applications error: {str(e)}")
        applications = []
    
    return render_template('recruiter/job_applications.html', job=job, applications=applications)

@recruiter.route('/applications/update-status', methods=['POST'])
@recruiter_login_required
def update_application_status():
    """Update application status (accept for interview, reject, hire)"""
    application_id = request.form.get('application_id')
    status = request.form.get('status')
    notes = request.form.get('notes', '')
    reason = request.form.get('reason', '')
    interview_date_str = request.form.get('interview_date', '')
    
    if not application_id or not status:
        flash('Invalid request.', 'error')
        return redirect(url_for('recruiter.applications'))
    
    try:
        # Get the application and verify it belongs to this recruiter
        application = db.session.query(Application).join(Job)\
                                .filter(Application.application_id == application_id,
                                       Job.recruiter_id == session.get('recruiter_id')).first()
        
        if not application:
            flash('Application not found.', 'error')
            return redirect(url_for('recruiter.applications'))
        
        # Update application status
        old_status = application.status
        application.status = status
        
        # Handle interview date if provided
        if interview_date_str and status == 'interview':
            try:
                # Parse the datetime string from the form
                interview_date = datetime.fromisoformat(interview_date_str.replace('T', ' '))
                
                # Validate that the date is in the future
                if interview_date <= datetime.now():
                    flash('Interview date must be in the future.', 'error')
                    return redirect(url_for('recruiter.applications'))
                
                application.interview_date = interview_date
                
            except ValueError as e:
                print(f"Date parsing error: {str(e)}")
                flash('Invalid interview date format.', 'error')
                return redirect(url_for('recruiter.applications'))
        
        # Add notes if provided
        if notes:
            application.notes = notes
        
        # Add rejection reason if provided and status is rejected
        if reason and status == 'rejected':
            application.rejection_reason = reason
        
        db.session.commit()
        
        # Flash appropriate message
        candidate_name = f"{application.candidate.first_name} {application.candidate.last_name}"
        if status == 'interview':
            if interview_date_str:
                interview_date_formatted = datetime.fromisoformat(interview_date_str.replace('T', ' ')).strftime('%B %d, %Y at %I:%M %p')
                flash(f'Interview scheduled with {candidate_name} for {interview_date_formatted}!', 'success')
            else:
                flash(f'Interview scheduled with {candidate_name}!', 'success')
        elif status == 'rejected':
            flash(f'Application from {candidate_name} has been rejected.', 'info')
        elif status == 'hired':
            flash(f'Congratulations! {candidate_name} has been hired!', 'success')
        elif status == 'shortlisted':
            flash(f'{candidate_name} has been shortlisted.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Application status update error: {str(e)}")
        flash('An error occurred while updating the application status.', 'error')
    
    return redirect(url_for('recruiter.applications'))

@recruiter.route('/candidate-profile')
@recruiter_login_required
def get_candidate_profile():
    """Get candidate profile data for modal display"""
    application_id = request.args.get('application_id')
    
    if not application_id:
        return jsonify({'success': False, 'error': 'Application ID required'})
    
    try:
        # Get the application and verify it belongs to this recruiter
        application = db.session.query(Application).join(Job)\
                                .filter(Application.application_id == application_id,
                                       Job.recruiter_id == session.get('recruiter_id')).first()
        
        if not application:
            return jsonify({'success': False, 'error': 'Application not found'})
        
        # Get candidate and user data
        candidate = application.candidate
        user = candidate.user
        job = application.job
        
        # Prepare response data
        candidate_data = {
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'email': user.email,
            'phone': candidate.phone,
            'location': candidate.location,
            'years_experience': candidate.years_experience,
            'candidate_skills': candidate.candidate_skills,
            'resume_file_path': candidate.resume_file_path
        }
        
        application_data = {
            'application_id': application.application_id,
            'status': application.status,
            'application_date': application.application_date.isoformat(),
            'interview_date': application.interview_date.isoformat() if application.interview_date else None,
            'match_score': application.match_score,
            'notes': application.notes,
            'rejection_reason': application.rejection_reason
        }
        
        job_data = {
            'job_id': job.job_id,
            'title': job.title,
            'location': job.location
        }
        
        return jsonify({
            'success': True,
            'candidate': candidate_data,
            'application': application_data,
            'job': job_data
        })
        
    except Exception as e:
        print(f"Get candidate profile error: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while fetching the profile'})

@recruiter.route('/candidates')
@recruiter_login_required
def candidates():
    """Search candidates route"""
    try:
        candidates = Candidate.query.all()
    except Exception as e:
        print(f"Candidates error: {str(e)}")
        candidates = []
    
    return render_template('recruiter/candidates.html', candidates=candidates)

@recruiter.route('/analytics')
@recruiter_login_required
def analytics():
    """Recruiter analytics route"""
    # This will be implemented later
    return render_template('recruiter/analytics.html')