import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from models import db, Job, Candidate, Application
import re
import logging

class JobRecommendationEngine:
    """
    Advanced Job Recommendation Engine using comprehensive scoring system
    Combines Sentence Transformers for semantic understanding with structured scoring
    """
    
    def __init__(self):
        # Initialize Sentence Transformer model for job role matching
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logging.info("Sentence Transformer model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Sentence Transformer model: {str(e)}")
            # Fallback to None - will need to handle this in methods
            self.model = None
        
        self.job_embeddings = None
        self.job_ids = []
        self.is_fitted = False
        
    def preprocess_text(self, text):
        """Clean and preprocess text data"""
        if not text:
            return ""
        
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^a-zA-Z\s+#]', ' ', str(text).lower())
        
        # Handle common programming languages and technologies
        tech_replacements = {
            'c++': 'cpp',
            'c#': 'csharp',
            '.net': 'dotnet',
            'node.js': 'nodejs',
            'react.js': 'reactjs',
            'vue.js': 'vuejs',
            'angular.js': 'angularjs',
        }
        
        for old, new in tech_replacements.items():
            text = text.replace(old, new)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def parse_salary_range(self, salary_text):
        """
        Parse salary range from text
        Returns tuple of (min_salary, max_salary) or (None, None) if parsing fails
        """
        if not salary_text:
            return None, None
            
        try:
            # Remove currency symbols and other non-numeric characters
            cleaned = re.sub(r'[^\d\-\–\—\,\.\s]', '', str(salary_text))
            
            # Replace various dash types with standard dash
            cleaned = cleaned.replace('–', '-').replace('—', '-')
            
            # Remove commas from numbers
            cleaned = cleaned.replace(',', '')
            
            # Check if it's a range (contains dash)
            if '-' in cleaned:
                parts = cleaned.split('-')
                if len(parts) >= 2:
                    min_val = float(parts[0].strip())
                    max_val = float(parts[1].strip())
                    return min_val, max_val
            
            # If it's a single number, use it as both min and max
            single_val = float(cleaned.strip())
            return single_val, single_val
            
        except Exception as e:
            logging.warning(f"Failed to parse salary range '{salary_text}': {str(e)}")
            return None, None
    
    def calculate_job_role_score(self, candidate, job):
        """
        Calculate job role match score (0-40 points) using transformers
        """
        if not candidate.job_role or not job.title:
            return 0, "No job role information available"
        
        if self.model is None:
            # Fallback to keyword matching if transformer model is not available
            return self._fallback_job_role_score(candidate, job)
        
        try:
            # Use sentence transformers for semantic similarity
            candidate_role = self.preprocess_text(candidate.job_role)
            job_title = self.preprocess_text(job.title)
            
            # Generate embeddings
            embeddings = self.model.encode([candidate_role, job_title])
            
            # Calculate cosine similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            # Convert similarity to score (0-40 points)
            if similarity >= 0.9:  # Exact/very close match
                return 40, f"Excellent role match (similarity: {similarity:.2f})"
            elif similarity >= 0.7:  # Related/similar role
                score = 20 + (similarity - 0.7) * 50  # 20-30 points
                return min(score, 30), f"Good role match (similarity: {similarity:.2f})"
            elif similarity >= 0.5:  # Somewhat related
                score = 10 + (similarity - 0.5) * 25  # 10-15 points
                return score, f"Partial role match (similarity: {similarity:.2f})"
            else:  # Different role
                score = similarity * 20  # 0-10 points
                return score, f"Limited role match (similarity: {similarity:.2f})"
                
        except Exception as e:
            logging.error(f"Error in transformer-based role matching: {str(e)}")
            return self._fallback_job_role_score(candidate, job)
    
    def _fallback_job_role_score(self, candidate, job):
        """Fallback job role scoring using keyword matching"""
        candidate_role = candidate.job_role.lower()
        job_title = job.title.lower()
        
        # Exact match
        if candidate_role == job_title:
            return 40, "Perfect job role match"
        
        # Check if candidate role is contained in job title or vice versa
        if candidate_role in job_title or job_title in candidate_role:
            return 35, "Job title matches your role"
        
        # Check for keyword matches
        candidate_keywords = set(word.strip() for word in re.split(r'[,\s\-/]', candidate_role) if len(word.strip()) > 2)
        job_keywords = set(word.strip() for word in re.split(r'[,\s\-/]', job_title) if len(word.strip()) > 2)
        
        # Remove common words
        common_words = {'and', 'or', 'the', 'of', 'in', 'at', 'to', 'for', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall'}
        candidate_keywords = candidate_keywords - common_words
        job_keywords = job_keywords - common_words
        
        if not candidate_keywords or not job_keywords:
            return 5, "Insufficient role information for comparison"
        
        # Calculate keyword overlap
        common_keywords = candidate_keywords.intersection(job_keywords)
        if common_keywords:
            overlap_ratio = len(common_keywords) / min(len(candidate_keywords), len(job_keywords))
            if overlap_ratio >= 0.7:
                return 30, f"Strong role match: {', '.join(common_keywords)}"
            elif overlap_ratio >= 0.4:
                return 20, f"Good role match: {', '.join(common_keywords)}"
            elif overlap_ratio >= 0.2:
                return 15, f"Partial role match: {', '.join(common_keywords)}"
        
        return 5, "Limited role similarity"
    
    def calculate_experience_score(self, candidate, job):
        """
        Calculate experience match score (0-20 points)
        """
        candidate_exp = candidate.years_experience or 0
        required_exp = job.required_experience or 0
        
        if candidate_exp >= required_exp:
            return 20, f"You meet the experience requirement ({candidate_exp} >= {required_exp} years)"
        
        # Calculate deduction for each year less than required
        years_short = required_exp - candidate_exp
        deduction = min(years_short * 5, 15)  # Max deduction of 15 points
        score = max(20 - deduction, 5)  # Minimum score of 5
        
        return score, f"You have {years_short} year(s) less experience than required"
    
    def calculate_salary_score(self, candidate, job):
        """
        Calculate salary alignment score (0-15 points)
        """
        if not candidate.salary_expectation or not job.salary_range:
            return 7, "No salary information available for comparison"
        
        candidate_min, candidate_max = self.parse_salary_range(candidate.salary_expectation)
        job_min, job_max = self.parse_salary_range(job.salary_range)
        
        if candidate_min is None or job_min is None:
            return 7, "Could not parse salary information"
        
        # Use candidate's preferred salary (average if range provided)
        candidate_preferred = (candidate_min + candidate_max) / 2 if candidate_max else candidate_min
        
        # Use job's maximum salary for comparison
        job_offer = job_max if job_max else job_min
        
        if job_offer >= candidate_preferred:
            return 15, f"Job salary meets or exceeds your expectation"
        
        # Calculate percentage below preferred salary
        percentage_below = (candidate_preferred - job_offer) / candidate_preferred * 100
        
        if percentage_below <= 10:
            return 12, f"Job salary is slightly below your expectation ({percentage_below:.1f}% less)"
        elif percentage_below <= 20:
            return 10, f"Job salary is moderately below your expectation ({percentage_below:.1f}% less)"
        elif percentage_below <= 30:
            return 5, f"Job salary is significantly below your expectation ({percentage_below:.1f}% less)"
        else:
            return 0, f"Job salary is much lower than your expectation ({percentage_below:.1f}% less)"
    
    def calculate_location_score(self, candidate, job):
        """
        Calculate location match score (0-15 points)
        """
        if not candidate.preferred_job_location or not job.location:
            return 7, "No location information available for comparison"
        
        candidate_location = candidate.preferred_job_location.lower().strip()
        job_location = job.location.lower().strip()
        
        # Exact match
        if candidate_location == job_location:
            return 15, "Perfect location match"
        
        # Remote work special case
        if 'remote' in candidate_location and 'remote' in job_location:
            return 15, "Remote work location match"
        
        # Check if one contains the other (partial match)
        if candidate_location in job_location or job_location in candidate_location:
            return 12, "Location partially matches your preference"
        
        # Check for city/state/country matches by splitting and comparing parts
        candidate_parts = set(part.strip() for part in re.split(r'[,\s]', candidate_location) if part.strip())
        job_parts = set(part.strip() for part in re.split(r'[,\s]', job_location) if part.strip())
        
        common_parts = candidate_parts.intersection(job_parts)
        if common_parts:
            return 10, f"Location partially matches: {', '.join(common_parts)}"
        
        # Different location
        return 5, "Different location from your preference"
    
    def calculate_skills_score(self, candidate, job):
        """
        Calculate skills match score (0-10 points)
        """
        if not candidate.candidate_skills or not job.skills_required:
            return 5, "No skills information available for comparison"
        
        # Parse skills
        candidate_skills = set(
            skill.strip().lower() 
            for skill in candidate.candidate_skills.split(',')
            if skill.strip()
        )
        
        job_skills = set(
            skill.strip().lower() 
            for skill in job.skills_required.split(',')
            if skill.strip()
        )
        
        if not job_skills:
            return 5, "No required skills specified"
        
        # Calculate matching skills
        matching_skills = candidate_skills.intersection(job_skills)
        match_percentage = (len(matching_skills) / len(job_skills)) * 100
        
        # Award points proportionally
        score = (match_percentage / 100) * 10
        
        return score, f"{match_percentage:.1f}% of required skills match ({len(matching_skills)}/{len(job_skills)})"
    
    def calculate_comprehensive_score(self, candidate, job):
        """
        Calculate comprehensive matching score (0-100 points)
        Returns total score and breakdown of individual components
        """
        try:
            # Calculate individual component scores
            role_score, role_explanation = self.calculate_job_role_score(candidate, job)
            experience_score, experience_explanation = self.calculate_experience_score(candidate, job)
            salary_score, salary_explanation = self.calculate_salary_score(candidate, job)
            location_score, location_explanation = self.calculate_location_score(candidate, job)
            skills_score, skills_explanation = self.calculate_skills_score(candidate, job)
            
            # Calculate total score
            total_score = role_score + experience_score + salary_score + location_score + skills_score
            
            # Ensure score is within 0-100 range
            total_score = max(0, min(100, total_score))
            
            # Create detailed breakdown
            breakdown = {
                'total_score': round(total_score, 1),
                'components': {
                    'job_role': {
                        'score': round(role_score, 1),
                        'max_score': 40,
                        'explanation': role_explanation
                    },
                    'experience': {
                        'score': round(experience_score, 1),
                        'max_score': 20,
                        'explanation': experience_explanation
                    },
                    'salary': {
                        'score': round(salary_score, 1),
                        'max_score': 15,
                        'explanation': salary_explanation
                    },
                    'location': {
                        'score': round(location_score, 1),
                        'max_score': 15,
                        'explanation': location_explanation
                    },
                    'skills': {
                        'score': round(skills_score, 1),
                        'max_score': 10,
                        'explanation': skills_explanation
                    }
                }
            }
            
            return total_score, breakdown
            
        except Exception as e:
            logging.error(f"Error calculating comprehensive score: {str(e)}")
            return 0, {
                'total_score': 0,
                'components': {},
                'error': str(e)
            }
    
    def get_recommendations(self, candidate, num_recommendations=10, min_score=30):
        """
        Get job recommendations for a candidate using comprehensive scoring
        
        Args:
            candidate: Candidate object
            num_recommendations: Number of recommendations to return
            min_score: Minimum score threshold (0-100)
            
        Returns:
            List of tuples (job, score, breakdown)
        """
        try:
            # Get all approved and open jobs
            jobs = Job.query.filter_by(is_approved=True, status='open').all()
            
            if not jobs:
                logging.warning("No jobs available for recommendations")
                return []
            
            # Get jobs the candidate has already applied to
            applications = Application.query.filter_by(candidate_id=candidate.candidate_id).all()
            applied_job_ids = {app.job_id for app in applications}
            
            recommendations = []
            
            for job in jobs:
                # Skip jobs the candidate has already applied to
                if job.job_id in applied_job_ids:
                    continue
                
                # Calculate comprehensive score
                score, breakdown = self.calculate_comprehensive_score(candidate, job)
                
                # Only include jobs that meet minimum score threshold
                if score >= min_score:
                    recommendations.append((job, score, breakdown))
            
            # Sort by score (highest first)
            recommendations.sort(key=lambda x: x[1], reverse=True)
            
            # Limit to requested number
            recommendations = recommendations[:num_recommendations]
            
            logging.info(f"Generated {len(recommendations)} recommendations for candidate {candidate.candidate_id} using comprehensive scoring")
            return recommendations
            
        except Exception as e:
            logging.error(f"Error generating recommendations for candidate {candidate.candidate_id}: {str(e)}")
            return []
    
    def get_skill_match_details(self, candidate, job):
        """
        Get detailed skill matching information between candidate and job
        
        Returns:
            Dict with matching skills, missing skills, and match percentage
        """
        try:
            candidate_skills = set()
            if candidate.candidate_skills:
                candidate_skills = set(
                    skill.strip().lower() 
                    for skill in candidate.candidate_skills.split(',')
                    if skill.strip()
                )
            
            job_skills = set()
            if job.skills_required:
                job_skills = set(
                    skill.strip().lower() 
                    for skill in job.skills_required.split(',')
                    if skill.strip()
                )
            
            if not job_skills:
                return {
                    'matching_skills': [],
                    'missing_skills': [],
                    'match_percentage': 0
                }
            
            matching_skills = candidate_skills.intersection(job_skills)
            missing_skills = job_skills - candidate_skills
            
            match_percentage = (len(matching_skills) / len(job_skills)) * 100 if job_skills else 0
            
            return {
                'matching_skills': list(matching_skills),
                'missing_skills': list(missing_skills),
                'match_percentage': round(match_percentage, 1)
            }
            
        except Exception as e:
            logging.error(f"Error calculating skill match: {str(e)}")
            return {
                'matching_skills': [],
                'missing_skills': [],
                'match_percentage': 0
            }
    
    def explain_recommendation(self, candidate, job, score, breakdown):
        """
        Provide an explanation for why a job was recommended
        
        Returns:
            Dict with explanation details
        """
        try:
            skill_match = self.get_skill_match_details(candidate, job)
            
            reasons = []
            
            # Add reasons based on component scores
            components = breakdown.get('components', {})
            
            # Job role
            if components.get('job_role', {}).get('score', 0) >= 30:
                reasons.append("Excellent job role match")
            elif components.get('job_role', {}).get('score', 0) >= 20:
                reasons.append("Good job role match")
            
            # Experience
            if components.get('experience', {}).get('score', 0) >= 18:
                reasons.append("You meet the experience requirements")
            elif components.get('experience', {}).get('score', 0) >= 15:
                reasons.append("Your experience is close to requirements")
            
            # Skills
            if skill_match['matching_skills']:
                reasons.append(f"Matches {len(skill_match['matching_skills'])} of your skills")
            
            # Salary
            if components.get('salary', {}).get('score', 0) >= 12:
                reasons.append("Salary aligns with your expectations")
            
            # Location
            if components.get('location', {}).get('score', 0) >= 12:
                reasons.append("Great location match")
            
            # Overall match quality based on total score
            if score >= 80:
                match_quality = "Excellent"
            elif score >= 70:
                match_quality = "Very Good"
            elif score >= 60:
                match_quality = "Good"
            elif score >= 50:
                match_quality = "Fair"
            else:
                match_quality = "Limited"
            
            return {
                'reasons': reasons,
                'match_quality': match_quality,
                'similarity_score': round(score, 1),
                'skill_match': skill_match,
                'breakdown': breakdown
            }
            
        except Exception as e:
            logging.error(f"Error explaining recommendation: {str(e)}")
            return {
                'reasons': ["Based on your profile"],
                'match_quality': "Good",
                'similarity_score': round(score, 1) if score else 0,
                'skill_match': {'matching_skills': [], 'missing_skills': [], 'match_percentage': 0},
                'breakdown': breakdown
            }

# Global recommendation engine instance
recommendation_engine = JobRecommendationEngine()

def get_job_recommendations(candidate_id, num_recommendations=10):
    """
    Convenience function to get job recommendations for a candidate
    
    Args:
        candidate_id: ID of the candidate
        num_recommendations: Number of recommendations to return
        
    Returns:
        List of tuples (job, score, explanation)
    """
    try:
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            return []
        
        recommendations = recommendation_engine.get_recommendations(
            candidate, 
            num_recommendations=num_recommendations
        )
        
        # Add explanations to recommendations
        enhanced_recommendations = []
        for job, score, breakdown in recommendations:
            explanation = recommendation_engine.explain_recommendation(
                candidate, job, score, breakdown
            )
            enhanced_recommendations.append((job, score, explanation))
        
        return enhanced_recommendations
        
    except Exception as e:
        logging.error(f"Error getting recommendations for candidate {candidate_id}: {str(e)}")
        return []

def refresh_recommendation_engine():
    """Refresh the recommendation engine with latest job data"""
    try:
        # For the comprehensive scoring system, no fitting is required
        # as it calculates scores on-demand
        logging.info("Recommendation engine refreshed (comprehensive scoring system)")
        return True
    except Exception as e:
        logging.error(f"Error refreshing recommendation engine: {str(e)}")
        return False