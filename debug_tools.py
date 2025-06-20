from models import db, User, Candidate, Recruiter
from werkzeug.security import generate_password_hash, check_password_hash
import sys

def check_user_credentials(email, password):
    """Debug tool to check if user credentials are valid"""
    user = User.query.filter_by(email=email).first()
    
    if not user:
        print(f"No user found with email: {email}")
        return False
    
    print(f"User found: {user.user_id}, Type: {user.user_type}, Active: {user.is_active}")
    
    # Check password
    password_match = check_password_hash(user.password_hash, password)
    print(f"Password match: {password_match}")
    
    if user.user_type == 'job_seeker':
        candidate = Candidate.query.filter_by(user_id=user.user_id).first()
        if candidate:
            print(f"Candidate: {candidate.first_name} {candidate.last_name}")
        else:
            print("No candidate profile found")
    elif user.user_type == 'recruiter':
        recruiter = Recruiter.query.filter_by(user_id=user.user_id).first()
        if recruiter:
            print(f"Recruiter: {recruiter.company_name}")
        else:
            print("No recruiter profile found")
    
    return password_match

def reset_user_password(email, new_password):
    """Reset a user's password"""
    user = User.query.filter_by(email=email).first()
    
    if not user:
        print(f"No user found with email: {email}")
        return False
    
    try:
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        print(f"Password reset successful for user: {email}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error resetting password: {str(e)}")
        return False

def list_all_users():
    """List all users in the database"""
    users = User.query.all()
    
    print(f"Total users: {len(users)}")
    for user in users:
        print(f"ID: {user.user_id}, Email: {user.email}, Type: {user.user_type}, Active: {user.is_active}")

if __name__ == "__main__":
    # This script can be run directly for debugging
    from app import create_app
    app = create_app()
    
    with app.app_context():
        if len(sys.argv) < 2:
            print("Usage: python debug_tools.py [check_credentials|reset_password|list_users]")
            sys.exit(1)
        
        command = sys.argv[1]
        
        if command == "check_credentials":
            if len(sys.argv) < 4:
                print("Usage: python debug_tools.py check_credentials [email] [password]")
                sys.exit(1)
            
            email = sys.argv[2]
            password = sys.argv[3]
            check_user_credentials(email, password)
        
        elif command == "reset_password":
            if len(sys.argv) < 4:
                print("Usage: python debug_tools.py reset_password [email] [new_password]")
                sys.exit(1)
            
            email = sys.argv[2]
            new_password = sys.argv[3]
            reset_user_password(email, new_password)
        
        elif command == "list_users":
            list_all_users()
        
        else:
            print("Unknown command. Available commands: check_credentials, reset_password, list_users")
