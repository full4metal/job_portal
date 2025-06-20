from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, CompanyReview, Recruiter, Candidate
from werkzeug.security import generate_password_hash
from datetime import datetime
import re
import uuid

# Import sentiment analysis libraries
try:
    from textblob import TextBlob
    SENTIMENT_AVAILABLE = True
except ImportError:
    try:
        import nltk
        from nltk.sentiment import SentimentIntensityAnalyzer
        # Download required NLTK data if not present
        try:
            nltk.data.find('vader_lexicon')
        except LookupError:
            nltk.download('vader_lexicon')
        SENTIMENT_AVAILABLE = True
    except ImportError:
        SENTIMENT_AVAILABLE = False

# Create Blueprint
sentiment = Blueprint('sentiment', __name__, url_prefix='/company')

def analyze_sentiment(text):
    """
    Analyze sentiment of review text using available libraries
    Returns sentiment score between -1 (negative) and 1 (positive)
    """
    if not text or not SENTIMENT_AVAILABLE:
        return 0.0
    
    try:
        # Try TextBlob first (simpler and more reliable)
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        return round(polarity, 3)
    except:
        try:
            # Fallback to NLTK VADER
            sia = SentimentIntensityAnalyzer()
            scores = sia.polarity_scores(text)
            # Convert compound score (-1 to 1) to our scale
            return round(scores['compound'], 3)
        except:
            # Manual sentiment analysis as last resort
            return manual_sentiment_analysis(text)

def manual_sentiment_analysis(text):
    """
    Simple manual sentiment analysis using keyword matching
    Returns sentiment score between -1 and 1
    """
    if not text:
        return 0.0
    
    text = text.lower()
    
    # Positive keywords
    positive_words = [
        'excellent', 'amazing', 'great', 'good', 'fantastic', 'wonderful', 
        'outstanding', 'perfect', 'love', 'best', 'awesome', 'brilliant',
        'satisfied', 'happy', 'pleased', 'recommend', 'professional',
        'helpful', 'friendly', 'efficient', 'quality', 'impressive'
    ]
    
    # Negative keywords
    negative_words = [
        'terrible', 'awful', 'bad', 'horrible', 'worst', 'hate', 'disappointing',
        'poor', 'unprofessional', 'rude', 'slow', 'inefficient', 'useless',
        'frustrated', 'angry', 'dissatisfied', 'complaint', 'problem',
        'issue', 'difficult', 'unresponsive', 'unreliable'
    ]
    
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    total_words = len(text.split())
    if total_words == 0:
        return 0.0
    
    # Calculate sentiment score
    sentiment_score = (positive_count - negative_count) / max(total_words / 10, 1)
    return max(-1.0, min(1.0, sentiment_score))

def get_sentiment_label(score):
    """Convert sentiment score to human-readable label"""
    if score > 0.1:
        return 'positive'
    elif score < -0.1:
        return 'negative'
    else:
        return 'neutral'

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

@sentiment.route('/review', methods=['GET', 'POST'])
@candidate_login_required
def submit_review():
    """Handle company review submissions"""
    
    if request.method == 'POST':
        errors = {}
        
        # Get form data
        recruiter_id = request.form.get('recruiter_id')
        rating = request.form.get('rating')
        review_text = request.form.get('review_text', '').strip()
        
        # Validate form data
        if not recruiter_id:
            errors['recruiter_id'] = "Please select a company to review."
        else:
            try:
                recruiter_id = int(recruiter_id)
                recruiter = Recruiter.query.get(recruiter_id)
                if not recruiter:
                    errors['recruiter_id'] = "Invalid company selected."
            except ValueError:
                errors['recruiter_id'] = "Invalid company selected."
        
        if not rating:
            errors['rating'] = "Please provide a rating."
        else:
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    errors['rating'] = "Rating must be between 1 and 5 stars."
            except ValueError:
                errors['rating'] = "Invalid rating provided."
        
        if not review_text:
            errors['review_text'] = "Please provide a detailed review."
        elif len(review_text) < 50:
            errors['review_text'] = "Review must be at least 50 characters long."
        elif len(review_text) > 2000:
            errors['review_text'] = "Review must be less than 2000 characters."
        
        # Check if user has already reviewed this company
        candidate_id = session.get('candidate_id')
        existing_review = CompanyReview.query.filter_by(
            recruiter_id=recruiter_id,
            candidate_id=candidate_id
        ).first()
        
        if existing_review:
            errors['general'] = "You have already reviewed this company."
        
        # If no errors, create the review
        if not errors:
            try:
                # Analyze sentiment
                sentiment_score = analyze_sentiment(review_text)
                
                # Create new review
                new_review = CompanyReview(
                    recruiter_id=recruiter_id,
                    candidate_id=candidate_id,
                    rating=rating,
                    review_text=review_text,
                    sentiment_score=sentiment_score,
                    review_date=datetime.utcnow()
                )
                
                db.session.add(new_review)
                db.session.commit()
                
                flash('Your review has been submitted successfully!', 'success')
                return redirect(url_for('sentiment.view_reviews', recruiter_id=recruiter_id))
                
            except Exception as e:
                db.session.rollback()
                print(f"Review submission error: {str(e)}")
                flash('An error occurred while submitting your review. Please try again.', 'error')
        
        # If there are errors, get companies for the form
        try:
            companies = Recruiter.query.all()
        except Exception as e:
            companies = []
            print(f"Error fetching companies: {str(e)}")
        
        return render_template('candidate/review.html', 
                             companies=companies, 
                             errors=errors,
                             form_data=request.form)
    
    # GET request - show review form
    try:
        companies = Recruiter.query.all()
    except Exception as e:
        companies = []
        print(f"Error fetching companies: {str(e)}")
        flash('Unable to load companies at this time.', 'error')
    
    return render_template('candidate/review.html', companies=companies)

@sentiment.route('/reviews')
@sentiment.route('/reviews/<int:recruiter_id>')
def view_reviews(recruiter_id=None):
    """Display company reviews with pagination and statistics"""
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    try:
        if recruiter_id:
            # Get specific company reviews
            recruiter = Recruiter.query.get_or_404(recruiter_id)
            
            # Get paginated reviews
            reviews_query = CompanyReview.query.filter_by(recruiter_id=recruiter_id)\
                                              .order_by(CompanyReview.review_date.desc())
            
            reviews_pagination = reviews_query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
            
            reviews = reviews_pagination.items
            
            # Calculate statistics
            all_reviews = CompanyReview.query.filter_by(recruiter_id=recruiter_id).all()
            
            if all_reviews:
                total_reviews = len(all_reviews)
                average_rating = sum(review.rating for review in all_reviews) / total_reviews
                
                # Sentiment distribution
                positive_reviews = len([r for r in all_reviews if r.sentiment_score > 0.1])
                negative_reviews = len([r for r in all_reviews if r.sentiment_score < -0.1])
                neutral_reviews = total_reviews - positive_reviews - negative_reviews
                
                # Rating distribution
                rating_distribution = {}
                for i in range(1, 6):
                    rating_distribution[i] = len([r for r in all_reviews if r.rating == i])
                
                stats = {
                    'total_reviews': total_reviews,
                    'average_rating': round(average_rating, 1),
                    'positive_reviews': positive_reviews,
                    'negative_reviews': negative_reviews,
                    'neutral_reviews': neutral_reviews,
                    'rating_distribution': rating_distribution
                }
            else:
                stats = {
                    'total_reviews': 0,
                    'average_rating': 0,
                    'positive_reviews': 0,
                    'negative_reviews': 0,
                    'neutral_reviews': 0,
                    'rating_distribution': {i: 0 for i in range(1, 6)}
                }
            
            return render_template('candidate/review.html',
                                 recruiter=recruiter,
                                 reviews=reviews,
                                 pagination=reviews_pagination,
                                 stats=stats,
                                 get_sentiment_label=get_sentiment_label)
        
        else:
            # Get all companies with their review stats
            companies = Recruiter.query.all()
            company_stats = []
            
            for company in companies:
                company_reviews = CompanyReview.query.filter_by(recruiter_id=company.recruiter_id).all()
                
                if company_reviews:
                    avg_rating = sum(r.rating for r in company_reviews) / len(company_reviews)
                    total_reviews = len(company_reviews)
                else:
                    avg_rating = 0
                    total_reviews = 0
                
                company_stats.append({
                    'company': company,
                    'average_rating': round(avg_rating, 1),
                    'total_reviews': total_reviews
                })
            
            # Sort by average rating (highest first)
            company_stats.sort(key=lambda x: x['average_rating'], reverse=True)
            
            return render_template('candidate/review.html',
                                 company_stats=company_stats)
    
    except Exception as e:
        print(f"Error loading reviews: {str(e)}")
        flash('Unable to load reviews at this time.', 'error')
        return render_template('candidate/review.html')

@sentiment.route('/api/sentiment-analysis', methods=['POST'])
def api_sentiment_analysis():
    """API endpoint for real-time sentiment analysis"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        sentiment_score = analyze_sentiment(text)
        sentiment_label = get_sentiment_label(sentiment_score)
        
        return jsonify({
            'sentiment_score': sentiment_score,
            'sentiment_label': sentiment_label,
            'text_length': len(text)
        })
        
    except Exception as e:
        print(f"Sentiment analysis API error: {str(e)}")
        return jsonify({'error': 'Analysis failed'}), 500

@sentiment.route('/api/company-stats/<int:recruiter_id>')
def api_company_stats(recruiter_id):
    """API endpoint for company review statistics"""
    try:
        recruiter = Recruiter.query.get_or_404(recruiter_id)
        reviews = CompanyReview.query.filter_by(recruiter_id=recruiter_id).all()
        
        if not reviews:
            return jsonify({
                'company_name': recruiter.company_name,
                'total_reviews': 0,
                'average_rating': 0,
                'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0}
            })
        
        total_reviews = len(reviews)
        average_rating = sum(review.rating for review in reviews) / total_reviews
        
        # Sentiment distribution
        positive = len([r for r in reviews if r.sentiment_score > 0.1])
        negative = len([r for r in reviews if r.sentiment_score < -0.1])
        neutral = total_reviews - positive - negative
        
        return jsonify({
            'company_name': recruiter.company_name,
            'total_reviews': total_reviews,
            'average_rating': round(average_rating, 1),
            'sentiment_distribution': {
                'positive': positive,
                'negative': negative,
                'neutral': neutral
            }
        })
        
    except Exception as e:
        print(f"Company stats API error: {str(e)}")
        return jsonify({'error': 'Unable to fetch stats'}), 500