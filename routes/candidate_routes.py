from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, Candidate, Job, Application, Recommendation, CompanyReview
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import re
from datetime import datetime
from routes.recommendation_engine import get_job_recommendations, refresh_recommendation_engine

# Create Blueprint
candidate = Blueprint('candidate', __name__, url_prefix='/candidate')

def candidate_login_required(f):
    """Decorator to require candidate login"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('main.login'))
        
        if session.get('user_type') != 'job_seeker':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@candidate.route('/register', methods=['GET', 'POST'])
def register():
    """Candidate registration route"""
    errors = {}
    
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        job_role = request.form.get('job_role', '').strip()
        skills = request.form.get('skills', '').strip()
        years_experience = request.form.get('years_experience', '0')
        
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
        
        if not first_name:
            errors['first_name'] = "First name is required."
        
        if not last_name:
            errors['last_name'] = "Last name is required."
        
        # If no errors, create the user
        if not errors:
            try:
                # Create user with explicit hashing method
                password_hash = generate_password_hash(password, method='pbkdf2:sha256')
                print(f"Registration - Generated password hash for {email}: {password_hash}")
                
                new_user = User(
                    email=email,
                    password_hash=password_hash,
                    user_type='job_seeker'
                )
                db.session.add(new_user)
                db.session.flush()  # Get the user_id without committing
                
                # Create candidate profile
                new_candidate = Candidate(
                    user_id=new_user.user_id,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone if phone else None,
                    location=location if location else None,
                    job_role=job_role if job_role else None,
                    candidate_skills=skills if skills else None,
                    years_experience=int(years_experience) if years_experience else 0
                )
                db.session.add(new_candidate)
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
    
    return render_template('candidate/register.html', errors=errors)

@candidate.route('/dashboard')
@candidate_login_required
def dashboard():
    """Candidate dashboard route"""
    candidate_id = session.get('candidate_id')
    
    if not candidate_id:
        flash('Profile not found. Please contact support.', 'error')
        return redirect(url_for('main.logout'))
    
    candidate = Candidate.query.get(candidate_id)
    
    if not candidate:
        flash('Profile not found. Please contact support.', 'error')
        return redirect(url_for('main.logout'))
    
    # Get dashboard statistics
    try:
        stats = {
            'total_applications': Application.query.filter_by(candidate_id=candidate_id).count(),
            'pending_applications': Application.query.filter_by(candidate_id=candidate_id, status='applied').count(),
            'interview_invites': Application.query.filter_by(candidate_id=candidate_id, status='interview').count(),
            'total_jobs': Job.query.filter_by(is_approved=True, status='open').count()
        }
        print("Candidate ID:", candidate_id)
        print("Stats:", stats)
        
        # Get recent applications
        recent_applications = Application.query.filter_by(candidate_id=candidate_id)\
                                             .order_by(Application.application_date.desc())\
                                             .limit(5).all()
        
        # Get job recommendations using ML-based system
        try:
            enhanced_recommendations = get_job_recommendations(candidate_id, num_recommendations=5)
            recommended_jobs = []
            
            for job, similarity_score, explanation in enhanced_recommendations:
                job.recommendation_score = similarity_score
                job.recommendation_explanation = explanation
                recommended_jobs.append(job)
                
        except Exception as e:
            print(f"Recommendation error: {str(e)}")
            # Fallback to simple recommendations
            recommended_jobs = Job.query.filter_by(is_approved=True, status='open')\
                                        .order_by(Job.posted_date.desc())\
                                        .limit(5).all()
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        stats = {'total_applications': 0, 'pending_applications': 0, 'interview_invites': 0, 'total_jobs': 0}
        recent_applications = []
        recommended_jobs = []
    
    return render_template('candidate/dashboard.html', 
                         candidate=candidate, 
                         stats=stats,
                         recent_applications=recent_applications,
                         recommended_jobs=recommended_jobs)

@candidate.route('/profile')
@candidate_login_required
def profile():
    """Candidate profile route"""
    candidate_id = session.get('candidate_id')
    candidate = Candidate.query.get(candidate_id)
    return render_template('candidate/profile.html', candidate=candidate)

@candidate.route('/profile/edit', methods=['GET', 'POST'])
@candidate_login_required
def edit_profile():
    """Edit candidate profile route"""
    candidate_id = session.get('candidate_id')
    candidate = Candidate.query.get(candidate_id)
    
    if not candidate:
        flash('Profile not found. Please contact support.', 'error')
        return redirect(url_for('candidate.dashboard'))
    
    errors = {}
    
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        job_role = request.form.get('job_role', '').strip()
        skills = request.form.get('skills', '').strip()
        years_experience = request.form.get('years_experience', '0')
        salary_expectation = request.form.get('salary_expectation', '').strip()
        preferred_job_location = request.form.get('preferred_job_location', '').strip()
        
        # Validate form data
        if not first_name:
            errors['first_name'] = "First name is required."
        elif len(first_name) > 50:
            errors['first_name'] = "First name must be less than 50 characters."
        
        if not last_name:
            errors['last_name'] = "Last name is required."
        elif len(last_name) > 50:
            errors['last_name'] = "Last name must be less than 50 characters."
        
        if phone and len(phone) > 15:
            errors['phone'] = "Phone number must be less than 15 characters."
        
        if location and len(location) > 100:
            errors['location'] = "Location must be less than 100 characters."
        
        if job_role and len(job_role) > 100:
            errors['job_role'] = "Job role must be less than 100 characters."
        
        if skills and len(skills) > 1000:
            errors['skills'] = "Skills list is too long. Please keep it under 1000 characters."
        
        if salary_expectation and len(salary_expectation) > 50:
            errors['salary_expectation'] = "Salary expectation must be less than 50 characters."
        
        if preferred_job_location and len(preferred_job_location) > 100:
            errors['preferred_job_location'] = "Preferred job location must be less than 100 characters."
        
        # Validate years of experience
        try:
            years_exp = int(years_experience) if years_experience else 0
            if years_exp < 0 or years_exp > 50:
                errors['years_experience'] = "Years of experience must be between 0 and 50."
        except ValueError:
            errors['years_experience'] = "Please enter a valid number for years of experience."
        
        # If no errors, update the profile
        if not errors:
            try:
                candidate.first_name = first_name
                candidate.last_name = last_name
                candidate.phone = phone if phone else None
                candidate.location = location if location else None
                candidate.job_role = job_role if job_role else None
                candidate.candidate_skills = skills if skills else None
                candidate.years_experience = int(years_experience) if years_experience else 0
                candidate.salary_expectation = salary_expectation if salary_expectation else None
                candidate.preferred_job_location = preferred_job_location if preferred_job_location else None
                
                db.session.commit()
                
                # Update session name if changed
                session['user_name'] = f"{first_name} {last_name}"
                
                flash('Profile updated successfully!', 'success')
                return redirect(url_for('candidate.profile'))
                
            except Exception as e:
                db.session.rollback()
                print(f"Profile update error: {str(e)}")
                flash('An error occurred while updating your profile. Please try again.', 'error')
    
    return render_template('candidate/edit_profile.html', candidate=candidate, errors=errors)

@candidate.route('/jobs')
@candidate_login_required
def jobs():
    """Job search route for candidates"""
    try:
        # Get all approved and open jobs
        jobs = Job.query.filter_by(is_approved=True, status='open')\
                       .order_by(Job.posted_date.desc()).all()
        
        # Get unique locations for filter dropdown
        locations = db.session.query(Job.location).filter_by(is_approved=True, status='open')\
                             .distinct().all()
        locations = [loc[0] for loc in locations if loc[0]]
        
        # Get unique skills for filter dropdown
        all_skills = []
        for job in jobs:
            if job.skills_required:
                skills = [skill.strip() for skill in job.skills_required.split(',')]
                all_skills.extend(skills)
        
        # Get unique skills and sort them
        skills = sorted(list(set(all_skills)))
        
    except Exception as e:
        print(f"Jobs error: {str(e)}")
        jobs = []
        locations = []
        skills = []
    
    return render_template('candidate/jobs.html', jobs=jobs, locations=locations, skills=skills)

@candidate.route('/applications')
@candidate_login_required
def applications():
    """Candidate applications route"""
    candidate_id = session.get('candidate_id')
    try:
        applications = Application.query.filter_by(candidate_id=candidate_id)\
                                      .order_by(Application.application_date.desc()).all()
        
        # Add current datetime for template comparisons
        now = datetime.utcnow()

    except Exception as e:
        print(f"Applications error: {str(e)}")
        applications = []
        now = datetime.utcnow()
    
    return render_template('candidate/applications.html', applications=applications, now=now)

@candidate.route('/apply', methods=['POST'])
@candidate_login_required
def apply_job():
    """Apply to a job route"""
    job_id = request.form.get('job_id')
    candidate_id = session.get('candidate_id')
    
    if not job_id or not candidate_id:
        flash('Invalid application request.', 'error')
        return redirect(url_for('candidate.jobs'))
    
    try:
        # Check if job exists and is available
        job = Job.query.filter_by(job_id=job_id, is_approved=True, status='open').first()
        if not job:
            flash('This job is no longer available.', 'error')
            return redirect(url_for('candidate.jobs'))
        
        # Check if already applied
        existing_application = Application.query.filter_by(
            job_id=job_id, 
            candidate_id=candidate_id
        ).first()
        
        if existing_application:
            flash('You have already applied to this job.', 'info')
            return redirect(url_for('candidate.jobs'))
        
        # Create new application
        new_application = Application(
            job_id=job_id,
            candidate_id=candidate_id,
            status='applied',
            match_score=0.0  # This could be calculated based on skills matching
        )
        
        db.session.add(new_application)
        db.session.commit()
        
        flash(f'Successfully applied to "{job.title}" at {job.recruiter.company_name}!', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Application error: {str(e)}")
        flash('An error occurred while submitting your application. Please try again.', 'error')
    
    return redirect(url_for('candidate.jobs'))

@candidate.route('/mark-interview-complete', methods=['POST'])
@candidate_login_required
def mark_interview_complete():
    """Mark interview as complete (update status to shortlisted)"""
    application_id = request.form.get('application_id')
    candidate_id = session.get('candidate_id')
    
    if not application_id or not candidate_id:
        flash('Invalid request.', 'error')
        return redirect(url_for('candidate.applications'))
    
    try:
        # Get the application and verify it belongs to this candidate
        application = Application.query.filter_by(
            application_id=application_id,
            candidate_id=candidate_id
        ).first()
        
        if not application:
            flash('Application not found.', 'error')
            return redirect(url_for('candidate.applications'))
        
        # Check if application is in interview status
        if application.status != 'interview':
            flash('This application is not in interview status.', 'error')
            return redirect(url_for('candidate.applications'))
        
        # Update status to shortlisted
        application.status = 'shortlisted'
        # application.status = 'shortlisted'
        
        db.session.commit()
        
        job_title = application.job.title
        flash(f'Interview for "{job_title}" marked as complete. Status updated to Interview Completed.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Mark interview complete error: {str(e)}")
        flash('An error occurred while updating the application status.', 'error')
    
    return redirect(url_for('candidate.applications'))

@candidate.route('/recommendations')
@candidate_login_required
def recommendations():
    """Get personalized job recommendations for the candidate"""
    candidate_id = session.get('candidate_id')
    
    try:
        # Get enhanced recommendations
        enhanced_recommendations = get_job_recommendations(candidate_id, num_recommendations=20)
        
        # Prepare data for template
        recommendations_data = []
        for job, similarity_score, explanation in enhanced_recommendations:
            recommendations_data.append({
                'job': job,
                'similarity_score': similarity_score,
                'explanation': explanation
            })
        
        candidate = Candidate.query.get(candidate_id)
        
        return render_template('candidate/recommendations.html', 
                             recommendations=recommendations_data,
                             candidate=candidate)
        
    except Exception as e:
        print(f"Recommendations page error: {str(e)}")
        flash('Unable to load recommendations at this time.', 'error')
        return redirect(url_for('candidate.dashboard'))

@candidate.route('/api/refresh-recommendations', methods=['POST'])
@candidate_login_required
def refresh_recommendations():
    """API endpoint to refresh recommendations"""
    try:
        # For the comprehensive scoring system, no fitting is required
        # The system calculates scores on-demand, so we just return success
        success = refresh_recommendation_engine()
        
        if success:
            return jsonify({
                'status': 'success', 
                'message': 'Recommendations refreshed successfully'
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': 'Failed to refresh recommendations'
            })
    except Exception as e:
        print(f"Refresh recommendations error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Error refreshing recommendations: {str(e)}'
        })