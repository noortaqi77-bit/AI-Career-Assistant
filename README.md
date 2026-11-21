# AI CAREER ASSISTANT

AI Career Assistant is an AI-powered platform that analyzes CVs, identifies relevant job opportunities, highlights skill gaps, suggests CV improvements, and provides live mock interview practice to help job seekers advance their careers.

## Problem Statement & motivation
Job seekers need more than a CV to navigate the recruitment process. They need to understand their qualifications, find relevant job opportunities, improve their CVs, and prepare for interviews. AI Career Assistant was developed to support these needs through AI-powered tools in one platform.

## Dataset description & sources 
AI Career Assistant uses two main data sources:

- CV Data: User-uploaded CVs in PDF format, which are processed to extract information such as education, work experience, skills, and certifications.
  
- Job Listings ( JSearch API): Job postings are retrieved through the JSearch API, which provides structured information such as job titles, company names, descriptions, locations, and employment requirements. These listings are used to identify relevant opportunities and evaluate the alignment between candidate qualifications and job requirements.
    source=(https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)


Uploaded CVs are processed during the session only and are not stored in this repository.

## Model architecture
No model is trained in this project. It uses pre-trained models through APIs.

| Component | Model / Tool | Role |
|---|---|---|
| Language model | `baidu/ernie-5.5-flash-preview:free` via OpenRouter | Interviewer questions, answer evaluation, CV feedback, CV edit suggestions |
| Text-to-speech | HeyGen `heygen-voice-1-turbo-free` | Interviewer voice (Noor) |
| Speech-to-text | Google Speech Recognition via `SpeechRecognition` | Converts spoken answers to text |
| Live audio and video | `streamlit-webrtc` | Microphone and camera in the browser |
| CV reading and editing | PyMuPDF, python-docx, pdf2docx | Read PDF/DOCX, edit and export Word |


