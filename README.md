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
The system uses Large Language Models (LLM) to interpret extracted CV information, analyse job descriptions, identify skill gaps, generate CV improvement recommendations, and evaluate interview responses.

| Component | Model / Tool | Role |
|---|---|---|
| Language model | `baidu/ernie-5.5-flash-preview:free` via OpenRouter | Interviewer questions, answer evaluation, CV feedback, CV edit suggestions |
| Text-to-speech | HeyGen `heygen-voice-1-turbo-free` | Interviewer voice (Noor) |
| Speech-to-text | Google Speech Recognition via `SpeechRecognition` | Converts spoken answers to text |
| Live audio and video | `streamlit-webrtc` | Microphone and camera in the browser |
| CV reading and editing | PyMuPDF, python-docx, pdf2docx | Read PDF/DOCX, edit and export Word |

**Pipeline**

- **Tab 1:** CV → skills → JSearch jobs → match score
- **Tab 2:** job + CV → interviewer question → voice (TTS) → spoken answer → text (STT) → next question → final evaluation (clarity, confidence, relevance, feedback)
- **Tab 3:** CV → feedback → edit suggestions (original / suggestion / reason) → user accepts edits → edited Word file

## Evaluation results & baseline comparison 


## How to run the project 

1. Clone the repository:

```bash
git clone https://github.com/[YOUR-USERNAME]/ai-career-assistant.git
cd ai-career-assistant
```

2. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.streamlit/secrets.toml` and add `OPENROUTER_KEY`, `HEYGEN_KEY` and `JSEARCH_KEY`.

4. Run the app:

```bash
streamlit run cv_app.py
```
## Repo structure 
ai-career-assistant/

├── cv_app.py

├── function_app.py

├── requirements.txt

├── notebook.ipynb

├── images/

│   ├── noor_idle.png

│   └── noor_talk.gif

├── presentation/

│   ├── slides.pptx

│   └── demo.mp4

├── .gitignore

└── README.md

## Limitations
-The application relies on a free-tier language model, which may result in response delays or temporary service unavailability due to usage restrictions.
-AI-generated CV recommendations may not always be fully accurate or relevant and should be reviewed by users before implementation.
-Editing PDF-based CVs requires conversion to Word format, which may affect the original document's formatting and layout.
The speech recognition feature is currently limited to English and does not support other languages.
  
## Future work
 -Collect jobs on a schedule and store them in a CSV file or database.
- Add body-language and voice feedback to the interview.
- Export a downloadable interview report.
- Introduce additional interview assessment features to provide more comprehensive feedback.

## Screenshots & Demo

**Demo video:** [Watch the demo](https://www.youtube.com/watch?v=QPtWgWxouJg&feature=youtu.be)
