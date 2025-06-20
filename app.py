from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from flask_wtf.csrf import CSRFProtect

from models import db
from routes.main_routes import main
from routes.candidate_routes import candidate
from routes.recruiter_routes import recruiter
from routes.admin_routes import admin
from routes.sentiment import sentiment

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # Change this in production
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql://root:@localhost/jobportal')  # Update with your MySQL credentials
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    csrf = CSRFProtect(app)
    
    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(candidate)
    app.register_blueprint(recruiter)
    app.register_blueprint(admin)
    app.register_blueprint(sentiment)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)