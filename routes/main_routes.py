from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, Candidate, Recruiter, Job, Application
from werkzeug.security import check_password_hash
from flask_wtf.csrf import CSRFProtect
import re

# Create Blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Landing page route with dynamic stats"""
    # Get real-time statistics from database
    try:
        stats = {
            'total_jobs': Job.query.filter_by(is_approved=True, status='open').count(),
            'total_candidates': Candidate.query.count(),
            'total_companies': Recruiter.query.count(),
            'success_rate': 100  # This could be calculated based on hired applications
        }
    except Exception as e:
        # Fallback stats if database is not available
        stats = {
            'total_jobs': 0,
            'total_candidates': 0,
            'total_companies': 0,
            'success_rate': 0
        }
        print(f"Database error in index: {str(e)}")
    
    return render_template('index.html', stats=stats)

@main.route('/login', methods=['GET', 'POST'])
def login():
    """Login page route with authentication"""
    errors = {}
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember')
        
        # Validate form data
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors['email'] = "Please enter a valid email address."
        
        if not password:
            errors['password'] = "Password is required."
        
        # If no validation errors, check credentials
        if not errors:
            try:
                user = User.query.filter_by(email=email).first()
                
                # Debug information
                print(f"Login attempt for email: {email}")
                print(f"User found: {user is not None}")
                
                if user:
                    # Debug password check
                    print(f"Stored hash: {user.password_hash}")
                    print(f"Input password: {password}")
                    
                    password_match = check_password_hash(user.password_hash, password)
                    print(f"Password match: {password_match}")
                    print(f"User active: {user.is_active}")
                    print(f"User type: {user.user_type}")
                    
                    if password_match and user.is_active:
                        # Login successful - create session
                        session.clear()  # Clear any existing session data
                        session['user_id'] = user.user_id
                        session['user_type'] = user.user_type
                        session['email'] = user.email
                        
                        # Get user's name for session
                        if user.user_type == 'job_seeker':
                            candidate = Candidate.query.filter_by(user_id=user.user_id).first()
                            if candidate:
                                session['user_name'] = f"{candidate.first_name} {candidate.last_name}"
                                session['candidate_id'] = candidate.candidate_id
                            else:
                                session['user_name'] = 'Candidate'
                                print("Warning: No candidate profile found for job_seeker")
                        elif user.user_type == 'recruiter':
                            recruiter = Recruiter.query.filter_by(user_id=user.user_id).first()
                            if recruiter:
                                session['user_name'] = recruiter.contact_person or recruiter.company_name
                                session['recruiter_id'] = recruiter.recruiter_id
                                session['company_name'] = recruiter.company_name
                            else:
                                session['user_name'] = 'Recruiter'
                                print("Warning: No recruiter profile found for recruiter")
                        elif user.user_type == 'admin':
                            session['user_name'] = 'Administrator'
                        
                        flash(f'Welcome back, {session.get("user_name", "User")}!', 'success')
                        
                        # Redirect based on user type
                        if user.user_type == 'job_seeker':
                            return redirect(url_for('candidate.dashboard'))
                        elif user.user_type == 'recruiter':
                            return redirect(url_for('recruiter.dashboard'))
                        elif user.user_type == 'admin':
                            return redirect(url_for('admin.dashboard'))
                        else:
                            return redirect(url_for('main.index'))
                    else:
                        if not user.is_active:
                            errors['general'] = "Your account has been deactivated. Please contact support."
                        else:
                            errors['general'] = "Invalid email or password. Please try again."
                else:
                    errors['general'] = "Invalid email or password. Please try again."
                    
            except Exception as e:
                print(f"Login error: {str(e)}")
                errors['general'] = "A system error occurred. Please try again later."
    
    return render_template('login.html', errors=errors)

@main.route('/register')
def register():
    """General registration page route"""
    return render_template('register.html')

@main.route('/logout')
def logout():
    """Logout route"""
    user_name = session.get('user_name', 'User')
    session.clear()
    flash(f'Goodbye, {user_name}! You have been logged out.', 'info')
    return redirect(url_for('main.index'))

# Helper function to check if user is logged in
def login_required(user_types=None):
    """Decorator to require login for certain routes"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('main.login'))
            
            if user_types and session.get('user_type') not in user_types:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

# API Routes for dynamic data
@main.route('/api/stats')
def api_stats():
    """API endpoint for real-time statistics"""
    try:
        stats = {
            'total_jobs': Job.query.filter_by(is_approved=True, status='open').count(),
            'total_candidates': Candidate.query.count(),
            'total_companies': Recruiter.query.count(),
            'total_applications': Application.query.count(),
            'pending_jobs': Job.query.filter_by(is_approved=False).count()
        }
    except Exception as e:
        stats = {
            'total_jobs': 0,
            'total_candidates': 0,
            'total_companies': 0,
            'total_applications': 0,
            'pending_jobs': 0
        }
        print(f"API stats error: {str(e)}")
    
    return jsonify(stats)

@main.route('/api/recent-jobs')
def api_recent_jobs():
    """API endpoint for recent job postings"""
    try:
        recent_jobs = Job.query.filter_by(is_approved=True, status='open')\
                              .order_by(Job.posted_date.desc())\
                              .limit(5).all()
        
        jobs_data = []
        for job in recent_jobs:
            jobs_data.append({
                'job_id': job.job_id,
                'title': job.title,
                'company': job.recruiter.company_name,
                'location': job.location,
                'salary_range': job.salary_range,
                'posted_date': job.posted_date.strftime('%Y-%m-%d')
            })
        
        return jsonify(jobs_data)
    except Exception as e:
        print(f"API recent jobs error: {str(e)}")
        return jsonify([])
