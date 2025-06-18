import spacy
import os
import re
import csv
from datetime import datetime
from PyPDF2 import PdfReader
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Loading NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")


TECH_KEYWORDS = [
    "python", "java", "javascript", "JS","C++", "C#", "php", "ruby", "go", "swift", "kotlin",
    "HTML", "CSS", "sass", "less", "typescript", "react", "angular", "vue", "Django", 
    "flask", "spring", "laravel", "node.js", "express", "SQL", "MySQL", "postgresql", 
    "mongoDB", "redis", "oracle", "cassandra", "aws", "azure", "GCP", "docker", 
    "kubernetes", "terraform", "ansible", "machine learning", "ML","deep learning","DL","nlp", 
    "computer vision", "tensorflow", "pytorch", "scikit-learn", "keras", "opencv", 
    "spark", "hadoop", "tableau", "powerbi", "git", "jenkins", "ci/cd", "agile", 
    "scrum", "rest api", "graphql", "microservices"
]

def extract_text(file_path: str) -> str:
    """Extract text from PDF or DOCX files"""
    try:
        if file_path.endswith('.pdf'):
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                return " ".join([page.extract_text() or "" for page in reader.pages])
                
        elif file_path.endswith('.docx'):
            doc = Document(file_path)
            return " ".join([para.text for para in doc.paragraphs])
            
        return ""
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def preprocess(text: str) -> str:

    """Cleaning and lemmatizing text using SpaCy"""

    if not text:
        return ""
    
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    
    doc = nlp(text)
    tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
    return " ".join(tokens)

def extract_tech_stack(text: str) -> list[str]:

    """Extract tech stack keywords from text"""

    if not text:
        return []
    
    text_lower = text.lower()
    found_keywords = set()
    
    for keyword in TECH_KEYWORDS:
        if ' ' in keyword and keyword in text_lower:
            found_keywords.add(keyword.title())
            if len(found_keywords) >= 10:
                return list(found_keywords)
    
    words = re.findall(r'\b\w+\b', text_lower)
    word_set = set(words)
    
    for keyword in TECH_KEYWORDS:
        if ' ' not in keyword and keyword in word_set:
            found_keywords.add(keyword.title())
            if len(found_keywords) >= 10:
                break
    
    return list(found_keywords)[:10]

def calculate_similarity(job_desc: str, resumes: list[str]) -> list[float]:

    """Calculate TF-IDF cosine similarity between job desc and resumes"""

    documents = [job_desc] + resumes
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents)
    cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
    return cosine_similarities[0]

def extract_keywords(text: str, top_n: int = 15) -> list[str]:

    """Extract top keywords using TF-IDF"""

    if not text:
        return []
    
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf = vectorizer.fit_transform([text])
    feature_names = vectorizer.get_feature_names_out()
    sorted_indices = tfidf.toarray()[0].argsort()[::-1]
    return [feature_names[i] for i in sorted_indices[:top_n]]

def process_resumes(job_desc: str, resume_paths: list[str]) -> list[dict]:

    """Main processing pipeline for resumes"""

    clean_jd = preprocess(job_desc)
    jd_keywords = extract_keywords(clean_jd)
    
    results = []
    resume_texts = []
    
    # Processing each resume
    for path in resume_paths:
        filename = os.path.basename(path)
        raw_text = extract_text(path)
        
        if not raw_text:
            continue
            
        clean_text = preprocess(raw_text)
        resume_texts.append(clean_text)
        
        tech_stack = extract_tech_stack(raw_text)
        
        keyword_score = sum(1 for word in jd_keywords if word in clean_text) / len(jd_keywords)
        
        results.append({
            "filename": filename,
            "tech_stack": tech_stack,
            "keyword_score": round(keyword_score * 100, 2)
        })
    
    if resume_texts:
        similarity_scores = calculate_similarity(clean_jd, resume_texts)
        for i, score in enumerate(similarity_scores):
            results[i]["similarity_score"] = round(score * 100, 2)
            grand_score = (results[i]["keyword_score"] * 0.5) + (results[i]["similarity_score"] * 0.5)
            results[i]["grand_score"] = round(grand_score, 2)
    
    ranked_results = sorted(results, key=lambda x: x["grand_score"], reverse=True)
    
    for i, res in enumerate(ranked_results):
        res["rank"] = i + 1
    
    return ranked_results

def generate_report(results: list[dict], report_dir: str) -> str:

    """Generate CSV report with full details"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resume_report_{timestamp}.csv"
    filepath = os.path.join(report_dir, filename)
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["rank", "filename", "grand_score", "tech_stack", 
                      "keyword_score", "similarity_score"]
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for res in results:
            writer.writerow({
                "rank": res["rank"],
                "filename": res["filename"],
                "grand_score": res["grand_score"],
                "tech_stack": ", ".join(res["tech_stack"]),
                "keyword_score": res.get("keyword_score", 0),
                "similarity_score": res.get("similarity_score", 0)
            })
    
    return filename