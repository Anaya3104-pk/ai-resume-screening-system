"""
TalentScan AI — Resume Processing Engine
Handles:
  - Text extraction from PDF and DOCX
  - Skill extraction using NLP + keyword matching
  - Match score calculation against job requirements
"""

import re
import os
import spacy
from pdfminer.high_level import extract_text as pdf_extract_text
from docx import Document

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

# ─────────────────────────────────────────
#  Master Skills Database
#  Add more skills here as needed
# ─────────────────────────────────────────
ALL_SKILLS = {
    # Programming Languages
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php',
    'swift', 'kotlin', 'go', 'rust', 'scala', 'r', 'matlab', 'perl',

    # Web Development
    'html', 'css', 'react', 'angular', 'vue', 'node.js', 'nodejs', 'express',
    'django', 'flask', 'fastapi', 'spring', 'laravel', 'bootstrap', 'tailwind',
    'jquery', 'next.js', 'nuxt', 'gatsby', 'wordpress',
    'express.js', 'rest api', 'graphql', 'redux', 'tailwind css', 'typescript',

    # Databases
    'mysql', 'postgresql', 'mongodb', 'sqlite', 'redis', 'oracle', 'sql server',
    'firebase', 'dynamodb', 'cassandra', 'elasticsearch',

    # Data Science & ML
    'machine learning', 'deep learning', 'neural networks', 'nlp',
    'natural language processing', 'computer vision', 'data analysis',
    'data visualization', 'statistics', 'pandas', 'numpy', 'scikit-learn',
    'tensorflow', 'pytorch', 'keras', 'opencv', 'matplotlib', 'seaborn',
    'tableau', 'power bi', 'excel', 'spss',

    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'jenkins',
    'ci/cd', 'terraform', 'ansible', 'linux', 'git', 'github', 'gitlab',
    'bitbucket', 'agile', 'scrum', 'jira', 'devops',

    # Design
    'figma', 'adobe xd', 'sketch', 'photoshop', 'illustrator', 'invision',
    'ui design', 'ux design', 'wireframing', 'prototyping', 'user research',

    # Project Management
    'project management', 'risk management', 'stakeholder management',
    'pmp', 'prince2', 'kanban', 'waterfall', 'budgeting', 'resource planning',

    # HR & Business
    'recruitment', 'talent acquisition', 'onboarding', 'performance management',
    'employee relations', 'hr policies', 'payroll', 'compensation', 'benefits',
    'hris', 'workday', 'sap hr', 'communication', 'leadership', 'teamwork',
    'problem solving', 'critical thinking', 'time management', 'presentation',

    # Networking
    'networking', 'tcp/ip', 'cybersecurity', 'firewall', 'vpn',
    'penetration testing', 'ethical hacking', 'iso 27001',
}

# ─────────────────────────────────────────
#  Job Role Required Skills
#  Maps each job role to its required skills
# ─────────────────────────────────────────
JOB_REQUIRED_SKILLS = {
    'software engineer': {
        'python', 'java', 'javascript', 'git', 'sql', 'mysql', 'postgresql',
        'html', 'css', 'react', 'nodejs', 'docker', 'agile', 'linux',
        'problem solving', 'teamwork'
    },
    'data analyst': {
        'python', 'r', 'sql', 'mysql', 'excel', 'pandas', 'numpy',
        'data analysis', 'data visualization', 'tableau', 'power bi',
        'statistics', 'matplotlib', 'communication', 'critical thinking'
    },
    'ui/ux designer': {
        'figma', 'adobe xd', 'sketch', 'ui design', 'ux design',
        'wireframing', 'prototyping', 'user research', 'html', 'css',
        'communication', 'teamwork', 'problem solving', 'presentation'
    },
    'project manager': {
        'project management', 'agile', 'scrum', 'jira', 'risk management',
        'stakeholder management', 'communication', 'leadership', 'budgeting',
        'resource planning', 'teamwork', 'time management', 'presentation'
    },
    'full stack developer': {
        'html', 'css', 'javascript', 'typescript', 'react', 'node.js',
        'python', 'mysql', 'mongodb', 'git', 'rest api', 'express.js',
        'bootstrap', 'php', 'postgresql', 'docker', 'aws', 'linux',
        'redux', 'next.js', 'tailwind css', 'graphql', 'firebase',
    },
    'full stack development': {
        'html', 'css', 'javascript', 'typescript', 'react', 'node.js',
        'python', 'mysql', 'mongodb', 'git', 'rest api', 'express.js',
        'bootstrap', 'php', 'postgresql', 'docker', 'aws', 'linux',
        'redux', 'next.js', 'tailwind css', 'graphql', 'firebase',
    },
    'hr business partner': {
        'recruitment', 'talent acquisition', 'onboarding', 'performance management',
        'employee relations', 'hr policies', 'communication', 'leadership',
        'problem solving', 'teamwork', 'payroll', 'hris', 'time management'
    },
}


# ─────────────────────────────────────────
#  1. TEXT EXTRACTION
# ─────────────────────────────────────────
def extract_text_from_pdf(filepath: str) -> str:
    """Extract raw text from a PDF file."""
    try:
        text = pdf_extract_text(filepath)
        return text or ''
    except Exception as e:
        print(f'PDF extraction error: {e}')
        return ''


def extract_text_from_docx(filepath: str) -> str:
    """Extract raw text from a DOCX file."""
    try:
        doc   = Document(filepath)
        lines = [para.text for para in doc.paragraphs]
        return '\n'.join(lines)
    except Exception as e:
        print(f'DOCX extraction error: {e}')
        return ''


def extract_text(filepath: str) -> str:
    """Auto-detect file type and extract text."""
    ext = filepath.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        return extract_text_from_pdf(filepath)
    elif ext in ('docx', 'doc'):
        return extract_text_from_docx(filepath)
    return ''


# ─────────────────────────────────────────
#  2. CANDIDATE INFO EXTRACTION
# ─────────────────────────────────────────
def extract_email(text: str) -> str:
    """Extract first email address found in text."""
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else ''


def extract_name(text: str) -> str:
    """Extract candidate name using spaCy NER."""
    try:
        doc = nlp(text[:500])  # Check first 500 chars
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                return ent.text.strip()
    except Exception:
        pass
    # Fallback: use first non-empty line
    for line in text.split('\n'):
        line = line.strip()
        if line and len(line.split()) <= 4 and len(line) > 3:
            return line
    return ''


# ─────────────────────────────────────────
#  3. SKILL EXTRACTION
# ─────────────────────────────────────────
def extract_skills(text: str) -> set:
    """
    Extract skills from resume text using keyword matching.
    Returns a set of matched skills.
    """
    text_lower = text.lower()
    found = set()

    for skill in ALL_SKILLS:
        # Use word boundary matching for accuracy
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.add(skill)

    return found


# ─────────────────────────────────────────
#  4. MATCH SCORE CALCULATION
# ─────────────────────────────────────────
def calculate_match_score(candidate_skills: set, job_title: str) -> int:
    """
    Compare candidate skills against required skills for the job.
    Returns a match percentage (0-100).
    """
    job_key = job_title.lower().strip()

    # Find the closest matching job in our database
    required_skills = None
    for key in JOB_REQUIRED_SKILLS:
        if key in job_key or job_key in key:
            required_skills = JOB_REQUIRED_SKILLS[key]
            break

    # If no specific role found, score based on total skills count
    if not required_skills:
        score = min(len(candidate_skills) * 5, 100)
        return score

    if not required_skills:
        return 0

    matched   = candidate_skills.intersection(required_skills)
    score     = round((len(matched) / len(required_skills)) * 100)
    return min(score, 100)


# ─────────────────────────────────────────
#  5. FULL PROCESSING PIPELINE
# ─────────────────────────────────────────
def process_resume(filepath: str, job_title: str = '') -> dict:
    """
    Full pipeline: extract text → extract info → score.
    Returns a dict with all extracted data.
    """
    # Extract text
    text = extract_text(filepath)

    if not text.strip():
        return {
            'success':    False,
            'error':      'Could not extract text from file.',
            'name':       '',
            'email':      '',
            'skills':     [],
            'score':      0,
        }

    # Extract candidate info
    name  = extract_name(text)
    email = extract_email(text)

    # Extract skills
    skills = extract_skills(text)

    # Calculate match score
    score = calculate_match_score(skills, job_title)

    return {
        'success': True,
        'name':    name,
        'email':   email,
        'skills':  sorted(list(skills)),
        'score':   score,
        'text':    text[:500],  # Store first 500 chars as preview
    }
