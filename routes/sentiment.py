from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, CompanyReview, Recruiter, Candidate
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import re
import uuid

# Import NLTK VADER sentiment analyzer
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
    Analyze sentiment of review text using NLTK's VADER sentiment analyzer
    Returns sentiment score between -1 (negative) and 1 (positive)
    """
    if not text or not SENTIMENT_AVAILABLE:
        return 0.0
    
    try:
        # Use NLTK VADER sentiment analyzer
        sia = SentimentIntensityAnalyzer()
        scores = sia.polarity_scores(text)
        
        # Return the compound score which ranges from -1 to 1
        # Compound score is the most useful single measure of sentiment
        return round(scores['compound'], 3)
        
    except Exception as e:
        print(f"VADER sentiment analysis error: {str(e)}")
        # Fallback to manual sentiment analysis if VADER fails
        return manual_sentiment_analysis(text)

def manual_sentiment_analysis(text):
    """
    Simple manual sentiment analysis using keyword matching as fallback
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
        'helpful', 'friendly', 'efficient', 'quality', 'impressive',
        'superb', 'exceptional', 'remarkable', 'terrific', 'marvelous'
    ]
    
    # Negative keywords
    negative_words = [
        'terrible', 'awful', 'bad', 'horrible', 'worst', 'hate', 'disappointing',
        'poor', 'unprofessional', 'rude', 'slow', 'inefficient', 'useless',
        'frustrated', 'angry', 'dissatisfied', 'complaint', 'problem',
        'issue', 'difficult', 'unresponsive', 'unreliable', 'pathetic',
        'disgusting', 'appalling', 'dreadful', 'atrocious', 'abysmal'
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
    """
    Convert VADER compound score to human-readable label
    Using standard VADER thresholds:
    - Positive: compound score >= 0.05
    - Negative: compound score <= -0.05
    - Neutral: -0.05 < compound score < 0.05
    """
    if score >= 0.05:
        return 'positive'
    elif score <= -0.05:
        return 'negative'
    else:
        return 'neutral'

def get_detailed_sentiment_scores(text):
    """
    Get detailed sentiment scores from VADER including positive, negative, neutral, and compound
    Returns dictionary with all VADER scores
    """
    if not text or not SENTIMENT_AVAILABLE:
        return {
            'positive': 0.0,
            'negative': 0.0,
            'neutral': 1.0,
            'compound': 0.0
        }
    
    try:
        sia = SentimentIntensityAnalyzer()
        scores = sia.polarity_scores(text)
        
        # Round all scores to 3 decimal places
        return {
            'positive': round(scores['pos'], 3),
            'negative': round(scores['neg'], 3),
            'neutral': round(scores['neu'], 3),
            'compound': round(scores['compound'], 3)
        }
        
    except Exception as e:
        print(f"Detailed VADER sentiment analysis error: {str(e)}")
        return {
            'positive': 0.0,
            'negative': 0.0,
            'neutral': 1.0,
            'compound': 0.0
        }

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
                # Analyze sentiment using VADER
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
    """Display company reviews with pagination, filtering, and statistics"""
    
    page = request.args.get('page', 1, type=int)
    rating_filter = request.args.get('rating', type=int)
    date_range_filter = request.args.get('date_range', '')
    company_filter = request.args.get('company', '')  # Now expects recruiter_id
    per_page = 10  # Limit to 10 reviews per page
    
    try:
        if recruiter_id:
            # Get specific company reviews
            recruiter = Recruiter.query.get_or_404(recruiter_id)
            show_all_reviews = False
            
            # Build query with filters
            reviews_query = CompanyReview.query.filter_by(recruiter_id=recruiter_id)
            
            # Apply rating filter
            if rating_filter:
                reviews_query = reviews_query.filter(CompanyReview.rating == rating_filter)
            
            # Apply date range filter
            if date_range_filter:
                now = datetime.utcnow()
                if date_range_filter == 'week':
                    start_date = now - timedelta(days=7)
                elif date_range_filter == 'month':
                    start_date = now - timedelta(days=30)
                elif date_range_filter == '3months':
                    start_date = now - timedelta(days=90)
                elif date_range_filter == 'year':
                    start_date = now - timedelta(days=365)
                else:
                    start_date = None
                
                if start_date:
                    reviews_query = reviews_query.filter(CompanyReview.review_date >= start_date)
            
            # Order by most recent first and paginate
            reviews_query = reviews_query.order_by(CompanyReview.review_date.desc())
            
            reviews_pagination = reviews_query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
            
            reviews = reviews_pagination.items
            
            # Calculate statistics for specific company
            all_reviews = CompanyReview.query.filter_by(recruiter_id=recruiter_id).all()
            
            if all_reviews:
                total_reviews = len(all_reviews)
                average_rating = sum(review.rating for review in all_reviews) / total_reviews
                
                # Sentiment distribution using VADER thresholds
                positive_reviews = len([r for r in all_reviews if r.sentiment_score >= 0.05])
                negative_reviews = len([r for r in all_reviews if r.sentiment_score <= -0.05])
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

        else:
            # Get all reviews from all companies
            recruiter = None
            show_all_reviews = True
            
            # Build query with filters
            reviews_query = CompanyReview.query.join(Recruiter)
            
            # Apply company filter (now using recruiter_id)
            if company_filter:
                try:
                    company_recruiter_id = int(company_filter)
                    reviews_query = reviews_query.filter(CompanyReview.recruiter_id == company_recruiter_id)
                except ValueError:
                    # If not a valid integer, ignore the filter
                    pass
            
            # Apply rating filter
            if rating_filter:
                reviews_query = reviews_query.filter(CompanyReview.rating == rating_filter)
            
            # Apply date range filter
            if date_range_filter:
                now = datetime.utcnow()
                if date_range_filter == 'week':
                    start_date = now - timedelta(days=7)
                elif date_range_filter == 'month':
                    start_date = now - timedelta(days=30)
                elif date_range_filter == '3months':
                    start_date = now - timedelta(days=90)
                elif date_range_filter == 'year':
                    start_date = now - timedelta(days=365)
                else:
                    start_date = None
                
                if start_date:
                    reviews_query = reviews_query.filter(CompanyReview.review_date >= start_date)
            
            # Order by most recent first and paginate
            reviews_query = reviews_query.order_by(CompanyReview.review_date.desc())
            
            reviews_pagination = reviews_query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
            
            reviews = reviews_pagination.items
            
            # Calculate statistics for all reviews (or filtered reviews)
            if company_filter or rating_filter or date_range_filter:
                # Use filtered results for stats
                filtered_reviews = reviews_query.all()
                all_reviews = filtered_reviews
            else:
                # Use all reviews for stats
                all_reviews = CompanyReview.query.all()
            
            if all_reviews:
                total_reviews = len(all_reviews)
                average_rating = sum(review.rating for review in all_reviews) / total_reviews
                
                # Sentiment distribution using VADER thresholds
                positive_reviews = len([r for r in all_reviews if r.sentiment_score >= 0.05])
                negative_reviews = len([r for r in all_reviews if r.sentiment_score <= -0.05])
                neutral_reviews = total_reviews - positive_reviews - negative_reviews
                
                # Rating distribution
                rating_distribution = {}
                for i in range(1, 6):
                    rating_distribution[i] = len([r for r in all_reviews if r.rating == i])
                
                # Company count
                total_companies = len(set(review.recruiter_id for review in all_reviews))
                
                stats = {
                    'total_reviews': total_reviews,
                    'average_rating': round(average_rating, 1),
                    'positive_reviews': positive_reviews,
                    'negative_reviews': negative_reviews,
                    'neutral_reviews': neutral_reviews,
                    'rating_distribution': rating_distribution,
                    'total_companies': total_companies
                }
            else:
                stats = {
                    'total_reviews': 0,
                    'average_rating': 0,
                    'positive_reviews': 0,
                    'negative_reviews': 0,
                    'neutral_reviews': 0,
                    'rating_distribution': {i: 0 for i in range(1, 6)},
                    'total_companies': 0
                }
        
        # Get companies for the review form dropdown and company filter
        try:
            companies = Recruiter.query.all()
        except Exception as e:
            companies = []
            print(f"Error fetching companies: {str(e)}")
        
        return render_template('candidate/review.html',
                             recruiter=recruiter,
                             reviews=reviews,
                             pagination=reviews_pagination,
                             stats=stats,
                             companies=companies,
                             show_all_reviews=show_all_reviews,
                             rating_filter=rating_filter,
                             date_range_filter=date_range_filter,
                             company_filter=company_filter,
                             get_sentiment_label=get_sentiment_label)
    
    except Exception as e:
        print(f"Error loading reviews: {str(e)}")
        flash('Unable to load reviews at this time.', 'error')
        return render_template('candidate/review.html')

@sentiment.route('/api/sentiment-analysis', methods=['POST'])
def api_sentiment_analysis():
    """API endpoint for real-time sentiment analysis using VADER"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Get detailed VADER scores
        detailed_scores = get_detailed_sentiment_scores(text)
        sentiment_score = detailed_scores['compound']
        sentiment_label = get_sentiment_label(sentiment_score)
        
        return jsonify({
            'sentiment_score': sentiment_score,
            'sentiment_label': sentiment_label,
            'text_length': len(text),
            'detailed_scores': detailed_scores
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
        
        # Sentiment distribution using VADER thresholds
        positive = len([r for r in reviews if r.sentiment_score >= 0.05])
        negative = len([r for r in reviews if r.sentiment_score <= -0.05])
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