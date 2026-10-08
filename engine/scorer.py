import re
import pymupdf  # PyMuPDF

# Keywords that trigger the Amber (Extended Response) badge
AMBER_KEYWORDS = [
    r"cover letter",
    r"portfolio",
    r"writing sample",
    r"assessment",
    r"take[- ]?home",
    r"challenge",
    r"case study"
]

def extract_resume_text(pdf_path: str) -> str:
    """
    Extract all text from the provided PDF resume.
    """
    try:
        doc = pymupdf.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        return text.lower()
    except Exception as e:
        print(f"Warning: Could not read resume PDF at {pdf_path}. Error: {e}")
        return ""

def calculate_match_score(job_desc: str, must_have_skills: list) -> int:
    """
    Calculate a match score (0-100) based on how many of the must-have skills
    are present in the job description.
    """
    if not job_desc or not must_have_skills:
        return 0

    desc_lower = job_desc.lower()
    
    matches = 0
    for skill in must_have_skills:
        # Use regex with word boundaries to match exact skills
        # e.g., to prevent "css" from matching inside "access"
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, desc_lower):
            matches += 1
            
    score = int((matches / len(must_have_skills)) * 100)
    return score

def determine_badge(job_desc: str) -> str:
    """
    Determine if a job requires extended responses (Amber) or is a quick apply (Slate).
    Scans the description for keywords like 'cover letter' or 'portfolio'.
    """
    if not job_desc:
        return "Slate"
        
    desc_lower = job_desc.lower()
    for keyword in AMBER_KEYWORDS:
        if re.search(keyword, desc_lower):
            return "Amber"
            
    return "Slate"

def score_jobs(jobs: list, resume_path: str, must_have_skills: list) -> list:
    """
    Process a list of jobs, score them, and assign badges.
    """
    resume_text = ""
    if resume_path:
        resume_text = extract_resume_text(resume_path)
        # Note: In a more advanced implementation, the resume text could be used
        # to dynamically extract skills or adjust the score based on keyword density
        # across both the resume and the job description. For now, we rely on the
        # explicit must_have_skills from the config.
        
    scored_jobs = []
    for job in jobs:
        desc = job.get("description", "")
        
        job["match_score"] = calculate_match_score(desc, must_have_skills)
        job["badge"] = determine_badge(desc)
        
        scored_jobs.append(job)
        
    # Sort by match score descending
    scored_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    
    return scored_jobs
