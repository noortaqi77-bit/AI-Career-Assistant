import streamlit as st
from openai import OpenAI
import json
import re
import queue
import requests
import numpy as np
import fitz
import docx
import speech_recognition as sr
import math
import os
import threading
import urllib.request


# the models
MODEL="baidu/ernie-5.5-flash-preview:free"
client=OpenAI(base_url="https://openrouter.ai/api/v1",api_key=st.secrets["OPENROUTER_KEY"])




# from the code(notebook) , read the cv if it's pdf or word 
def read_cv(cv):
    if cv.lower().endswith(".pdf"):
        doc=fitz.open(cv)
        return "\n".join(page.get_text() for page in doc)
    elif cv.lower().endswith(".docx"):
        d=docx.Document(cv)
        return "\n".join(p.text for p in d.paragraphs)
    else:
        raise ValueError("only use pdf or docx !!!!!")

# function of questions (TTS) 
def speak(text):
    voice_q=requests.post("https://api.heygen.com/v3/models/audio/tts",
        headers={"X-Api-Key": st.secrets["HEYGEN_KEY"], "Content-Type":"application/json"},
        json={
            "model": "heygen-voice-1-turbo-free",
            "voice_id": "83548de556df48ba8c09c42a57c51d85",
            "text":text,
            "language": "en",
        },
    )
    if voice_q.status_code == 200:
        return voice_q.json()["data"]["audio_url"]
    return None



# evalute the answers by the llm model by a prompt and return it 
def evaluate_answer(questions,answers):
    try:
        promti=f"""You are an interviewer. Evaluate the candidate's complete interview.
        The answers are speech-to-text transcripts: ignore small transcription errors, punctuation, grammar slips, and filler words.
        Questions and Answers:{json.dumps([ {"question": question, "answer": answers[i]}for i, question in enumerate(questions)], ensure_ascii=False)}
        Evaluate the overall interview and return ONLY valid JSON with exactly these keys:"clarity" (integer 1-10),"confidence" (integer 1-10),"relevance" (integer 1-10),"feedback" (one short paragraph).
"""
        llm_score=client.chat.completions.create(model="baidu/ernie-5.5-flash-preview:free",messages=[{"role": "user", "content": promti}],max_tokens=4000, temperature=0)
        raw=llm_score.choices[0].message.content.strip()                      
        cleaned=raw.replace("```json", "").replace("```","").strip() 
        # make it to python string 
        return json.loads(cleaned) 
       
        # to avoid error
    except Exception as e:
        print("Error:", e)
        return {"clarity": 5, "confidence": 5, "relevance": 5,
                "feedback": "Could not evaluate this answer."}   


#Scoring guide: 1-3 = off-topic or very incomplete, 4-6 = partly answers the question with limited detail, 7-8 = clear and relevant with some specifics, 9-10 = clear, specific, and well-structured.

# for live interview ,that give th equestions based on previous answer,then create a new Q from anthoer topic
def interviewer_reply(history, job_title, job_text, cv_part, level):
    system=f"""You are Noor, a friendly interviewer running a mock job interview. Difficulty level: {level}.
Ask ONE short question per turn (maximum 25 words). Each question must cover a NEW topic from the job requirements or the CV. Never repeat a topic. Do not dwell on the last answer, even if it was short or incomplete: move on to the next topic.
Do not give feedback and do not answer your own questions.
Job title: {job_title}
Job description: {job_text[:1500]}
{cv_part}"""
    messages=[{"role": "system", "content": system}]+history
    for attempt in range(3):
        r=client.chat.completions.create(model=MODEL,messages=messages, max_tokens=1500)
        text=r.choices[0].message.content
        if text:
            return text
    return None



# for tab 3 ,the llm model gives feedback based on the cv after using read_cv function
def cv_feedback(cv_text):
    prompt=f"""Write feedback on this CV in English.
First, one friendly sentence that addresses the candidate by their field or profession (for example "Hi Engineer," or "Hi Data Analyst,") and says the CV content is good, naming the most distinctive thing in it. Start the sentence with one friendly emoji. If the field is unclear, start with "Hi,".
Then write exactly 5 numbered tips to improve the content. Each tip says what to add, change or remove, and where in the CV (name the section or job).
Each tip is one sentence, maximum 25 words, in a friendly tone. Be specific to this CV. Never invent facts.
Format: write the greeting sentence in bold, then leave an empty line, then the 5 tips, each on its own line.
CV: {cv_text}"""
    r=client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}], max_tokens=4000)
    return r.choices[0].message.content


# for the next button , make suggestions (I add some details to fit the prompt )
def cv_suggestions(cv_text):
    prompt=f"""Suggest 5 to 8 content edits that make this CV stronger for recruiters. Return ONLY a JSON list.
Each item has the keys: "original" (text copied exactly from the CV), "suggestion" (the edited text), "reason" (one short sentence).
Do NOT make edits that only swap synonyms, and do NOT add placeholders or brackets. Only make edits that can be done using what the CV already says: remove skills or filler that no experience supports, delete repeated ideas, merge or shorten bullets, or start bullets with strong action verbs.
Do NOT suggest edits that only change punctuation, dashes, spacing or capitalisation.
Never invent facts, numbers or details. If an edit would need a number or detail that the CV does not contain, do not suggest it.
CV: {cv_text}"""
    for attempt in range(2):
        r=client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}], max_tokens=8000)
        text=r.choices[0].message.content
        if text:
            return json.loads(text[text.find("["):text.rfind("]")+1])
    return []



# tab3: after accept the edits , take the edits and pit them in the same file , same place:
def apply_edits(path,edits):
    d=docx.Document(path)
    paras=list(d.paragraphs)
    for t in d.tables:
        for row in t.rows:
            for cell in row.cells:
                paras+=cell.paragraphs
    for old, new in edits:
        # for the points
        old=old.replace("●", "").strip()
        new=new.replace("●", "").strip()
        pat=r"\s+".join(re.escape(w) for w in old.split())
        for p in paras:
            if p.runs and re.search(pat, p.text):
                p.runs[0].text=re.sub(pat, lambda m: new, p.text, count=1)
                for r in p.runs[1:]:
                    r.text=""
                break
    d.save("edited_cv.docx")
    return "edited_cv.docx"



# engry: to know when the user strat  talk and stop , measures how loud one audio frame
def frame_energy(frame):
    #the frame make them numbers , the convert the numbers(then to int32 so squaring does not overflow) 
    samples= np.frombuffer(frame.to_ndarray().tobytes(), dtype=np.int16).astype(np.int32)
    return np.sqrt(np.mean(samples**2))

# i choosed 2000 for talk and silent 100 and above 
def live_listen(ctx):
    silence_frames=0
    speaking=False
    chunks=[]
    rate=48000
    channels=1
    width=2
    while ctx.state.playing:
        try:
            frames=ctx.audio_receiver.get_frames(timeout=3)
        except queue.Empty:
            continue
        for audio_frame in frames:
            rate=audio_frame.sample_rate
            channels=len(audio_frame.layout.channels)
            width=audio_frame.format.bytes
            chunks.append(audio_frame.to_ndarray().flatten())
            if frame_energy(audio_frame)<2000:
                silence_frames+=1
            else:
                silence_frames=0
                speaking=True
        if not speaking:
            chunks=chunks[-25:]
        if speaking and silence_frames>=100:
            sound=np.concatenate(chunks)
            if channels>1:
                sound=sound.reshape(-1, channels).mean(axis=1).astype(np.int16)
            audio=sr.AudioData(sound.tobytes(), rate, width)
            try:
                # use google the detect the text
                return sr.Recognizer().recognize_google(audio,language="en-US")
            except Exception:
                chunks=[]
                speaking=False
                silence_frames=0
    return None

try:
    import mediapipe as mp
    POSE_FILE="pose_landmarker_lite.task"
    if not os.path.exists(POSE_FILE):
        urllib.request.urlretrieve("https://huggingface.co/litert-community/MediaPipe-PoseLandmarker-Lite/resolve/main/pose_landmarker_lite.task", POSE_FILE)
    landmarker=mp.tasks.vision.PoseLandmarker.create_from_options(
        mp.tasks.vision.PoseLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=POSE_FILE)))
except Exception:
    landmarker=None


body_lock=threading.Lock()
body_data={"n":0,"seen":0,"tilt":0.0,"away":0,"hands":0,"touch":0}

def reset_body_data():
    with body_lock:
        for k in body_data:
            body_data[k]=0



 # runs on every camera frame ; it only measures and returns the frame as it is
def body_frame_callback(frame):
    
    body_data["n"]+=1
    # analyse only every 5th frame so the video does not get slow
    if landmarker is None or body_data["n"]%5!=0:
        return frame
    try:
        # the frame as an RGB picture , then MediaPipe finds the body points
        rgb=frame.to_ndarray(format="rgb24")
        result=landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if result.pose_landmarks:
            p=result.pose_landmarks[0]
            # point numbers from MediaPipe : 0 nose , 7 and 8 ears , 15 and 16 wrists
            # head = the width of the head (distance between the ears) , used as a ruler
            head=abs(p[7].x-p[8].x)
            if head>0:
                #only the wrists that MediaPipe can really see in the picture
                wrists=[w for w in (p[15],p[16]) if w.visibility>0.5]
                with body_lock:
                    body_data["seen"]+=1
                    # looking away : the nose is far from the middle of the two ears
                    if abs(p[0].x-(p[7].x+p[8].x)/2)/head>0.25:
                        body_data["away"]+=1
                    # hands : at least one wrist is visible
                    if wrists:
                        body_data["hands"]+=1
                    # touching the face: a wrist is closer to the nose than the width of the head
                    if any(math.hypot(w.x-p[0].x,w.y-p[0].y)<head for w in wrists):
                        body_data["touch"]+=1
    except Exception:
        #a failed frame must never stop the camera
        pass
    return frame



# body_lock=threading.Lock()
# body_data={"n":0,"seen":0,"tilt":0.0,"away":0,"hands":0,"touch":0}

# def reset_body_data():
#     with body_lock:
#         for k in body_data:
#             body_data[k]=0


#called after Submit Interview -> turns the counters into percentages and asks the LLM for the sentences
def body_feedback():
    with body_lock:
        d=dict(body_data)
    # nobody was analysed [no camera, no mediapipe, or the body was not visible] will show nothing
    if d["seen"]==0:
        return ""
    pct=lambda x: round(100*x/d["seen"])
    numbers={"looking_away_from_camera_percent":pct(d["away"]),
             "hands_visible_percent":pct(d["hands"]),
             "hand_near_face_percent":pct(d["touch"])}
    prompt=("You are an interview coach. Measurements from the candidate's webcam during a mock interview: "+str(numbers)+". "
            "Write 3 short sentences of body-language feedback in the second person about looking at the camera, hands, and touching the face, "
            "based ONLY on these numbers. Do not mention the numbers themselves.")
    try:
        r=client.with_options(max_retries=3).chat.completions.create(model=MODEL,messages=[{"role":"user","content":prompt}],max_tokens=300)
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return ""
