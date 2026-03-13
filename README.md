# AI Resume Screening System

A web-based **AI Resume Screening System** built using **Python, Flask, NLP, and MySQL** to automate candidate evaluation and ranking for HR teams.

This system helps recruiters quickly analyze resumes, extract candidate skills, match them with job requirements, and generate a ranked list of the most suitable candidates.

---

## Project Overview

Recruiters often receive **hundreds of resumes** for a single job position. Manually reviewing each resume is time-consuming and inefficient.

The **AI Resume Screening System** automates this process by:

• Extracting text from uploaded resumes
• Identifying candidate skills using Natural Language Processing (NLP)
• Comparing candidate skills with job requirements
• Calculating a matching score
• Ranking candidates automatically

This helps HR teams **shortlist the best candidates faster and more efficiently**.

---

## Features

* HR login authentication system
* Resume upload system (PDF / DOCX)
* Resume text extraction
* Skill extraction using NLP
* Candidate scoring based on job requirements
* Automatic candidate ranking
* Candidate profile analysis
* Resume storage and processing
* Professional HR dashboard interface

---

## Technology Stack

### Backend

* Python
* Flask

### Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript

### Database

* MySQL

### Python Libraries

* mysql-connector-python
* pdfminer.six
* spaCy
* pandas
* scikit-learn

### Visualization

* Chart.js

### Development Tools

* Visual Studio Code
* Git & GitHub
* MySQL Workbench

---

## System Architecture

```
Resume Upload
      ↓
Resume Text Extraction
      ↓
Skill Extraction (NLP)
      ↓
Skill Matching
      ↓
Candidate Score Calculation
      ↓
Candidate Ranking
      ↓
HR Dashboard
```

---

## Project Structure

```
ai-resume-screening-system
│
├── templates/            # HTML pages
├── uploads/              # Uploaded resumes
│
├── app.py                # Flask backend application
├── resume_processor.py   # Resume parsing and skill extraction
├── schema.sql            # Database schema
├── requirements.txt      # Python dependencies
├── README.md
└── .gitignore
```

---

## Installation Guide

### 1. Clone the repository

```
git clone https://github.com/Anaya3104-pk/ai-resume-screening-system.git
```

### 2. Navigate to the project folder

```
cd ai-resume-screening-system
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Configure MySQL Database

Create a database in MySQL and import the schema:

```
source schema.sql
```

### 5. Run the Flask application

```
python app.py
```

The application will start at:

```
http://localhost:5000
```

---

## UI Design Principles

The project follows a **clean professional UI design** similar to enterprise HR software.

Design rules:

* Light green theme
* Solid colors (no gradients)
* Professional icons
* No emojis
* Minimal modern layout
* Clean dashboard interface

Fonts used:

* Inter
* Poppins

---

## Future Improvements

* Advanced AI resume ranking model
* Machine learning based candidate recommendation
* Email notifications for shortlisted candidates
* Multi-role authentication (HR / Candidate)
* Resume keyword highlighting
* Deployment on cloud platforms

---

## Team Members

**Anaya Kalap**
GitHub: https://github.com/Anaya3104-pk

**Mayukani Tayde**
GitHub: https://github.com/Mayuuu27

---

## License

This project is developed for **educational and demonstration purposes**.

