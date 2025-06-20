from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Database Models based on your schema
class User(db.Model):
    __tablename__ = 'Users'
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    user_type = db.Column(db.Enum('job_seeker', 'recruiter', 'admin'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    candidate = db.relationship('Candidate', backref='user', uselist=False)
    recruiter = db.relationship('Recruiter', backref='user', uselist=False)

class Candidate(db.Model):
    __tablename__ = 'Candidates'
    candidate_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15))
    location = db.Column(db.String(100))
    job_role = db.Column(db.String(100))
    candidate_skills = db.Column(db.Text)
    years_experience = db.Column(db.Integer)
    resume_file_path = db.Column(db.String(255))
    salary_expectation = db.Column(db.String(50))
    preferred_job_location = db.Column(db.String(100))
    
    # Relationships
    applications = db.relationship('Application', backref='candidate')
    reviews = db.relationship('CompanyReview', backref='candidate')
    recommendations = db.relationship('Recommendation', backref='candidate')

class Recruiter(db.Model):
    __tablename__ = 'Recruiters'
    recruiter_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'), unique=True, nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    company_description = db.Column(db.Text)
    contact_person = db.Column(db.String(100))
    company_location = db.Column(db.String(100))
    website_url = db.Column(db.String(255))
    reputation_score = db.Column(db.Float)
    
    # Relationships
    jobs = db.relationship('Job', backref='recruiter')
    reviews = db.relationship('CompanyReview', backref='recruiter')

class Job(db.Model):
    __tablename__ = 'Jobs'
    job_id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('Recruiters.recruiter_id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100))
    salary_range = db.Column(db.String(50))
    skills_required = db.Column(db.Text)
    required_experience = db.Column(db.Integer)
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum('open', 'closed', 'pending'), default='pending')
    is_approved = db.Column(db.Boolean, default=False)
    
    # Relationships
    applications = db.relationship('Application', backref='job')
    recommendations = db.relationship('Recommendation', backref='job')

class Application(db.Model):
    __tablename__ = 'Applications'
    application_id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('Jobs.job_id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('Candidates.candidate_id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    interview_date = db.Column(db.DateTime)
    status = db.Column(db.Enum('applied', 'shortlisted', 'interview', 'rejected', 'hired'), default='applied')
    match_score = db.Column(db.Float)
    notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

class CompanyReview(db.Model):
    __tablename__ = 'Company_Reviews'
    review_id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('Recruiters.recruiter_id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('Candidates.candidate_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.Text)
    review_date = db.Column(db.DateTime, default=datetime.utcnow)
    sentiment_score = db.Column(db.Float)

class Recommendation(db.Model):
    __tablename__ = 'Recommendations'
    recommendation_id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('Candidates.candidate_id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('Jobs.job_id'), nullable=False)
    recommendation_score = db.Column(db.Float, nullable=False)
    generated_date = db.Column(db.DateTime, default=datetime.utcnow)

class AdminAction(db.Model):
    __tablename__ = 'Admin_Actions'
    action_id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'), nullable=False)
    action_type = db.Column(db.Enum('approve_job', 'block_user', 'delete_job', 'other'), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    action_date = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text)