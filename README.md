## 🌟 Inspiration  
Job seekers often struggle to find roles that truly match their skills, expectations, and preferred locations. Recruiters, on the other hand, need better tools to assess fit beyond just resumes. I wanted to build a portal that intelligently connects the right candidates with the right jobs — using NLP and sentiment analysis to improve transparency and decision-making.

---

## 🚀 What it does  
- Allows candidates to create profiles, apply for jobs, and receive smart, personalized job recommendations.  
- Enables recruiters to post jobs, manage applications, and view applicant matches.  
- Admins can oversee the entire platform, approve jobs, and manage users.  
- Uses NLP-based job role matching and VADER sentiment analysis to:  
  - Recommend jobs based on role, experience, salary, location, and skills.  
  - Analyze company reviews to highlight positive/negative feedback for job seekers.

---

## 🛠️ How I built it  
- **Backend:** Python with Flask for routing and logic.  
- **Database:** MySQL to manage users, jobs, applications, and reviews.  
- **Recommendation Engine:** Used `SentenceTransformer (all-MiniLM-L6-v2)` for semantic matching and cosine similarity for scoring.  
- **Sentiment Analysis:** Integrated **VADER** to analyze text reviews and extract sentiment scores.  
- **Role-based Access:** Built separate dashboards for admins, recruiters, and candidates.  
- **Frontend:** HTML, CSS, and Bootstrap (optionally JavaScript and template rendering).

---


## 🏆 Accomplishments that I'am proud of  
- Built a fully functional multi-role portal with intelligent job matching.  
- Implemented a real-time recommendation engine using semantic similarity.  
- Enhanced the candidate experience with sentiment-based insights on companies.  
- Delivered meaningful feedback to users with explainable AI recommendations.

---


## 🔮 What's next for Job Management Portal  
- Implement collaborative filtering to incorporate user behavior for better job suggestions.  
- Enable resume upload and parsing using spaCy or third-party APIs.  
- Add recruiter-side recommendation (suggest matching candidates).  
- Improve UX/UI with modern frontend frameworks like React or Vue.  
- Deploy the platform on cloud (AWS/Azure) and enable notifications via email/SMS.
