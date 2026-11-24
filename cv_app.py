import streamlit as st
import fitz
from openai import OpenAI
import os
import json
import requests
import docx
from streamlit_mic_recorder import speech_to_text
from streamlit_webrtc import webrtc_streamer,WebRtcMode
import time
import re 
import queue
import numpy as np
import speech_recognition as sr
import streamlit.components.v1 as components
from pdf2docx import Converter
from function_app import read_cv, speak, evaluate_answer, interviewer_reply, cv_feedback, cv_suggestions, apply_edits, frame_energy,live_listen
from trafilatura import fetch_url,extract


st.markdown("""
<style>
.stButton > button { background-color: #1F3A68; color: white; border: none; }
.stButton > button:hover { background-color: #2B4C8C; color: white; }
.stApp { background-color: #E6ECF6; }
h1, h2, h3 { color: #1F3A68; font-weight: 700; }
[data-testid="stMetric"] { background-color: white; border: 1px solid #DDE3EE; border-radius: 12px; padding: 12px 16px; }
.stTabs [role="tablist"] { background: white !important; border-radius: 12px; padding: 6px; gap: 8px; box-shadow: 0 2px 8px rgba(31,58,104,0.12); border-bottom: none !important; }
.stTabs [role="tab"] { flex: 1; justify-content: center; border-radius: 8px; border: none !important; outline: none !important; box-shadow: none !important; }
.stTabs [role="tab"] p { color: #1F3A68; font-weight: 500; }
.stTabs [role="tab"][aria-selected="true"] { background: #1F3A68 !important; }
.stTabs [role="tab"][aria-selected="true"] p { color: white; font-weight: 600; }
.stTabs [role="tablist"] > div:not([role="tab"]), .stTabs [data-baseweb="tab-border"], .stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.hero { background: #1F3A68; border-radius: 12px; padding: 28px 36px; margin-bottom: 16px; }
.hero h1 { color: white; margin: 0; }
.hero p { color: #C9D5EA; margin: 6px 0 0; }
.jobcard { background: white; border: 1px solid #DDE3EE; border-radius: 12px; padding: 20px 24px; margin-bottom: 16px; }
.jobcard h3 { margin: 0; color: #1F3A68; }
.jobmeta { color: #4A5568; font-size: 14px; margin: 4px 0 12px; }
.match { float: right; border: 2px solid #1F3A68; border-radius: 12px; padding: 6px 14px; font-weight: 700; color: #1F3A68; font-size: 22px; }
.chip { display: inline-block; background: #DCE6F7; color: #1F3A68; padding: 4px 12px; border-radius: 999px; font-size: 13px; margin: 0 6px 6px 0; }
.chip-miss { display: inline-block; border: 1.5px dashed #4A5568; color: #4A5568; padding: 3px 12px; border-radius: 999px; font-size: 13px; margin: 0 6px 6px 0; }
.apply { display: inline-block; background: #1F3A68; color: white !important; padding: 8px 20px; border-radius: 8px; text-decoration: none; font-weight: 600; }
.qmeta { color: #4A5568; font-size: 13px; margin-bottom: 6px; }
.bar { height: 8px; background: #DCE6F7; border-radius: 999px; margin-bottom: 14px; }
.bar div { height: 8px; background: #1F3A68; border-radius: 999px; }
.qcard { background: white; border: 1px solid #DDE3EE; border-radius: 12px; padding: 24px 28px; font-size: 22px; font-weight: 600; color: #1F3A68; line-height: 1.4; margin-bottom: 14px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>AI Career Assistant</h1><p>Upload your CV, find matching jobs, then practise the interview.</p></div>', unsafe_allow_html=True)




# the models
MODEL="baidu/ernie-5.5-flash-preview:free"
client=OpenAI(base_url="https://openrouter.ai/api/v1",api_key=st.secrets["OPENROUTER_KEY"],max_retries=6)




st.set_page_config(  page_title="AI Career Assistant",layout="wide")
uploaded_file=st.file_uploader("   ", type=["pdf", "docx"])
tab1, tab2, tab3=st.tabs(["CV Analysis", "Mock Interview","CV Check"])






with tab1:
    st.info("JOBS IN BAHRAIN.🔎")

    # read the cv files :
    if uploaded_file is not None:
        open(uploaded_file.name, "wb").write(uploaded_file.getvalue())
        
    
        
        if st.button("Analyse"):
            cv_text=read_cv(uploaded_file.name)
            # extract the skills , education , experience and years:
            prompt=f"""Extract information from this CV. Return ONLY valid JSON with these keys: "skills" (list of technical skills),"soft_skills"(list),"education" (list), "experience" (list), "years_of_experience" (number).
                 
            CV:
            {cv_text}"""
            cv_data=None
            for attempt in range(3):
                cv_info=client.chat.completions.create(model=MODEL,messages=[{"role": "user","content": prompt}], max_tokens=3000)
                text=cv_info.choices[0].message.content
                if text:
                    try:
                        cv_data=json.loads(text[text.find("{"):text.rfind("}")+1])
                        break
                    except Exception:
                        cv_data=None
            if cv_data is None:
                st.error("Please press Analyse again.")
                st.stop()
            # cv_info=client.chat.completions.create(model=MODEL,messages=[{"role": "user","content": prompt}], max_tokens=3000)
            # text=cv_info.choices[0].message.content
            # cv_data=json.loads(text[text.find("{"):text.rfind("}")+1])
            # cv_data=json.loads(cv_info.choices[0].message.content.replace("```json", "").replace("```", "").strip())
            st.session_state.cv_data=cv_data
        
            # st.subheader("Your Profile")
            # st.json(cv_data)
    
            # the model will see Suggested job:  
            p=f"Give ONE job title closest to this candidate's skills, experience and field of study. Return ONLY the title.\n{json.dumps(cv_data)}"
            # add temperture to make constant results :
            x=client.chat.completions.create(model=MODEL,messages=[{"role": "user","content":p}],max_tokens=2000,temperature=0)
            # first, but the suggested job , then the jobs with skills :
            st.write("Suggested job : ",x.choices[0].message.content)

            cv_job=x.choices[0].message.content.strip()

            
            
            # copy from the notebook (Jsearch for the job , to compare )
            response=requests.get(
                "https://jsearch.p.rapidapi.com/search-v2",
                headers={"x-rapidapi-key": st.secrets["JSEARCH_KEY"], "x-rapidapi-host": "jsearch.p.rapidapi.com"},
                params={"query": f"{cv_job} in Bahrain", "num_pages": "1", "country": "bh", "date_posted": "all"},)
            
            #save the response 
            data=response.json()
    
            # I select the job title  , company name , describe of the job 
            jobs_raw=[{"title": j["job_title"],"company_name": j["employer_name"], "description": j.get("job_description") or "", "location": j.get("job_location"), "apply_link": j.get("job_apply_link")} for j in data["data"]["jobs"]]


            # the main prompt : find the  right jobs 
            prompt2=f"""Compare the candidate to each job. Return ONLY a JSON list, one item per job.
           Keys: "job_title", "matched_skills", "missing_skills".
           matched = a skill the job asks for that the candidate has. missing = a skill the job asks for that the candidate lacks.
           If the candidate has closely related experience for a skill, count it as matched.
           Only skills written in the job description: tools, techniques, soft skills, years or degree requirements. No job titles.
           Candidate: {json.dumps(cv_data)}
            Jobs: {json.dumps([{"title": j["title"],"description": j["description"][:1500]} for j in jobs_raw])}"""
            
            result=None
        # because it make error or none sometime,
            for attempt in range(2):
                r2=client.chat.completions.create(model=MODEL,messages=[{"role": "user", "content": prompt2}], max_tokens=8000)
                text=r2.choices[0].message.content
                if text:
                    result=json.loads(text.replace("```json", "").replace("```", "").strip())
                    break
            if result is None:
                st.error("Please press Analyse again.")
                st.stop()
            # from notebook 
            cv_years=cv_data["years_of_experience"]
            for job in result:
              # N.o match and missing 
                n_yes=len(job["matched_skills"])
                n_x=len(job["missing_skills"])
            
            
            
            
            #for each job 
                for j in jobs_raw:
                    if j["title"]==job["job_title"]:
                        text=j["description"]
                        years=text.lower().find("years")
                        # found 
                        if years != -1:
                            digits=""
                            # find the words before "years" word :
                            for i in text[max(0, years-12): years]:
                              # find the number 
                                if i.isdigit():
                                    digits+= i
                                elif digits:
                                    break
                            # count 
                            if digits:
                                if cv_years>=int(digits):
                                    n_yes+= 1
                                else:
                                    n_x+=1
                        break
            # calc the % of each job :
                job["final_percent"]=round(100 *n_yes/(n_yes+n_x)) if (n_yes+ n_x) else None
            result=sorted(result, key=lambda job: job["final_percent"] or 0, reverse=True)


            # new :
            st.session_state.top_jobs=[]
            # to save them
            info= {j["title"]: j for j in jobs_raw}
            
            st.subheader(" Top 3 matches job:  ")
            for job in result[:3]:
                jobs3=info.get(job["job_title"],{})
                #new
                st.session_state.top_jobs.append({"title": job["job_title"], "company": jobs3.get("company_name"), "description":jobs3.get("description", "")})           
                # the results :
                matched="".join(['<span class="chip">'+s+'</span>' for s in job["matched_skills"]])
                missing="".join(['<span class="chip-miss">'+s+'</span>' for s in job["missing_skills"]])
                apply_btn='<a class="apply" href="'+jobs3["apply_link"]+'" target="_blank">Apply</a>' if jobs3.get("apply_link") else ""
                card=('<div class="jobcard">'
                      '<div class="match">'+str(job["final_percent"])+'%</div>'
                      '<h3>'+job["job_title"]+'</h3>'
                      '<div class="jobmeta">'+str(jobs3.get("company_name"))+' · '+str(jobs3.get("location"))+'</div>'
                      '<div><b>Matched</b><br>'+matched+'</div>'
                      '<div style="margin-top:8px"><b>Missing</b><br>'+missing+'</div>'
                      '<div style="margin-top:12px">'+apply_btn+'</div>'
                      '</div>')
                st.markdown(card, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def job_text_from_link(url):
    try:
        page=fetch_url(url)
        return (extract(page) or "") if page else ""
    except Exception:
        return ""            

with tab2:
    st.write("Mock Interview tab")
        
    #new
    list_of_jobs=st.session_state.get("top_jobs", [])
    if "history" not in st.session_state:
        source=st.segmented_control("Job source", ["Analysis results", "Enter a job", "CV only"], default="Analysis results", label_visibility="collapsed")
        if source=="Analysis results":
            title_jobs=[i["title"]+"  -  "+ str(i["company"]) for i in list_of_jobs]
            select_jobs=st.selectbox("select the job that ",title_jobs)
            chose=list_of_jobs[title_jobs.index(select_jobs)] if select_jobs else None
            st.write(f"You choosed ",chose["title"] if chose else " nothing , do the analysis first")
        # second thing is by user's job , and i made the cv is optional <
        elif source=="Enter a job":
            custom_title=st.text_input("Job title")
            job_url=st.text_input("Job link (optional)")
            custom_desc=st.text_area("Or paste the job description here")
            if job_url and not custom_desc:
                custom_desc=job_text_from_link(job_url)
                if not custom_desc:
                    st.warning("Could not read this link. Please paste the job description instead.")
           
            # chose={"title": custom_title or "Not specified (infer the job from the description below)", "company": "Not specified", "description": custom_desc} if custom_desc else None
            # custom_title=st.text_input("Job title")
            # custom_desc=st.text_area("Paste the job description here")
            # chose={"title": custom_title or "Not specified (infer the job from the description below)", "company": "Not specified", "description": custom_desc} if custom_desc else None  
            chose={"title": custom_title or "Not specified (infer the job from the description below)", "company": "Not specified", "description": custom_desc} if custom_desc else None

        else:
            chose={"title":"General interview", "company": "Not specified", "description": "No specific job.Ask general interview questions based on the CV."}
        

        level=st.radio("Interview level",["Entry Level", "Mid Level", "Senior Level"],horizontal=True)
        
        if st.button("Start Interview") and chose:
            # to work without error with third option
            if source=="CV only" and uploaded_file is None:
                st.warning("Please upload your CV first.")
                st.stop()
            # write the prompt based on choice ;
            # from part 1 , take cv_data
            if "cv_data" in st.session_state:
                cv_part="Candidate CV:"+json.dumps(st.session_state.cv_data)
                # part of prompt , to merge them next step
                base="Base the questions on BOTH the candidate's CV and the job description: ask about the job's requirements, and about the candidate's relevant experience and gaps."

            # if not , upload the cv again , then open 
            elif uploaded_file is not None:
                open(uploaded_file.name, "wb").write(uploaded_file.getvalue())
                cv_part="Candidate CV:"+read_cv(uploaded_file.name)
                 # part of prompt , to merge them next step
                base="Base the questions on BOTH the candidate's CV and the job description: ask about the job's requirements, and about the candidate's relevant experience and gaps."
            else:
                cv_part=""
                # here the prompt , in none :
                base="Base the questions only on the job description: ask about the job's requirements and skills."
                
            
            Q_prompt=f"""Write 5 interview questions for the job below.{base}
            Return ONLY a JSON list of 5 strings.
            Each question must be one or two sentences ,maximum 20 words, with no sub-questions.
            Difficulty level: {level}
            Job title:{chose["title"]}
            Company:{chose["company"]}
            Job description:{chose["description"][:1500]}
            {cv_part}"""
    
            # chat_q=client.chat.completions.create(model=MODEL,messages=[{"role": "user", "content": Q_prompt}],max_tokens=3000,temperature=0)
            st.session_state.history=[]
            st.session_state.history.append({"role": "assistant", "content": interviewer_reply([], chose["title"], chose["description"], cv_part, level) or "Tell me about yourself."})
            st.session_state.job=chose
            st.session_state.cv_part=cv_part
            st.session_state.level=level
            # the index to count
            st.session_state.q_index=0
            st.session_state.answers={}
            st.session_state.audio={}
            st.session_state.audio[0]=speak(st.session_state.history[-1]["content"])
            st.session_state.start_time=time.time()
            st.rerun()

        
    if "q_index" in st.session_state:
        i=st.session_state.q_index
        # question=st.session_state.questions[i]
        question=st.session_state.history[-1]["content"]
        total=5
        pct=round((i+1)/total*100)
        q_slot=st.empty()
        q_html='<div class="qmeta">Question '+str(i+1)+' of '+str(total)+'</div><div class="bar"><div style="width:'+str(pct)+'%"></div></div><div class="qcard">'+question+'</div>'
        # st.markdown('<div class="qmeta">Question '+str(i+1)+' of '+str(total)+'</div><div class="bar"><div style="width:'+str(pct)+'%"></div></div><div class="qcard">'+question+'</div>', unsafe_allow_html=True)        #st.write("Question", i+1,"of",len(st.session_state.questions),":", question)

        # the mic
        # to make side for camera and side for mic
        col_cam,col_noor=st.columns([3, 1])
        st.markdown('<style>.st-key-noor_box{position:relative;width:150px;height:150px;margin:20px auto}.st-key-noor_gif{position:absolute;top:0;left:0;display:none}.st-key-noor_box.talk .st-key-noor_gif{display:block}.st-key-noor_box.talk .st-key-noor_idle{visibility:hidden}</style>', unsafe_allow_html=True)




        with col_noor:
            with st.container(key="noor_box"):
                with st.container(key="noor_idle"):
                   st.image("images/noor_idle.png",width=150)
                with st.container(key="noor_gif"):
                    st.image("images/noor_talk.gif",width=150)
        components.html('<script>const p=window.parent.document;setInterval(()=>{const au=[...p.querySelectorAll(".st-key-noor_audio audio")];const m=p.querySelector(".st-key-noor_box");if(m){if(au.some(x=>!x.paused)){m.classList.add("talk")}else{m.classList.remove("talk")}}},300)</script>', height=0)
        
        RTC={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        with col_cam:
            cam=webrtc_streamer(key="cam",rtc_configuration=RTC,media_stream_constraints={"video": True, "audio": False}, desired_playing_state=True, media_toggle_controls=True)
             # webrtc_streamer(key="cam",rtc_configuration=RTC,media_stream_constraints={"video": True, "audio": False}, desired_playing_state=True, media_toggle_controls=False)
            # webrtc_streamer(key="cam", rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}, media_stream_constraints={"video": True, "audio": False}, desired_playing_state=True, media_toggle_controls=False)
        live=True
        if live:
            finished=(i==total-1 and i in st.session_state.answers)
            if not finished:
                st.markdown('<style>.st-key-mic_box{display:none}</style>', unsafe_allow_html=True)
                with st.container(key="mic_box"):
                    ctx=webrtc_streamer(key="mic",rtc_configuration=RTC,mode=WebRtcMode.SENDONLY,audio_receiver_size=1024, media_stream_constraints={"video": False, "audio": True}, desired_playing_state=True)
                    
        
        
        
        if i not in st.session_state.audio:
            st.session_state.audio[i]=speak(question)
        url=st.session_state.audio[i]
        if url and cam.state.playing:
            st.markdown('<style>.st-key-noor_audio{display:none}</style>', unsafe_allow_html=True)
            with st.container(key="noor_audio"):
                st.audio(url, autoplay=True)
        q_slot.markdown(q_html, unsafe_allow_html=True)
        # if url:
        #     st.markdown('<style>.st-key-noor_audio{display:none}</style>', unsafe_allow_html=True)
        #     with st.container(key="noor_audio"):
        #         st.audio(url, autoplay=True)
           


        # voice part , using stt:
        if live:
        #     finished=(i==total-1 and i in st.session_state.answers)
        #     if not finished:
        #         st.markdown('<style>.st-key-mic_box{display:none}</style>', unsafe_allow_html=True)
        #         with st.container(key="mic_box"):
        #             ctx=webrtc_streamer(key="mic",rtc_configuration=RTC,mode=WebRtcMode.SENDONLY,audio_receiver_size=1024, media_stream_constraints={"video": False, "audio": True}, desired_playing_state=True)
                    # ctx=webrtc_streamer(key="mic", rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}, mode=WebRtcMode.SENDONLY, audio_receiver_size=1024, media_stream_constraints={"video": False, "audio": True}, desired_playing_state=True)
            answer=None
            if i not in st.session_state.answers and ctx.state.playing:
                note=st.empty()
                # note for the user
                note.write("Listening... answer,then stay quiet for 2 seconds.")
                answer=live_listen(ctx)
                note.empty()
        else:
            answer=speech_to_text(language="en",start_prompt="Start recording", stop_prompt="Stop recording",just_once=True,key=f"STT{i}")
        #to show the sentences to the user :
        if answer:
            st.session_state.answers[i]=answer
            st.write("Your answer:", answer)
        if live and answer and i<total-1:
            st.session_state.history.append({"role": "user", "content": st.session_state.answers[i]})
            st.session_state.history.append({"role": "assistant", "content": interviewer_reply(st.session_state.history,st.session_state.job["title"], st.session_state.job["description"], st.session_state.cv_part,st.session_state.level) or "Can you tell me more about your experience?"})
            st.session_state.audio[i+1]=speak(st.session_state.history[-1]["content"])
            st.session_state.q_index+=1
            st.rerun()

        # the rest or questions :
        if i < total-1:
            if st.button("Next"):
                if i in st.session_state.answers:
                    st.session_state.history.append({"role": "user", "content": st.session_state.answers[i]})
                    #
                    st.session_state.history.append({"role": "assistant", "content": interviewer_reply(st.session_state.history,st.session_state.job["title"], st.session_state.job["description"], st.session_state.cv_part,st.session_state.level) or "Can you tell me more about your experience?"})
                    st.session_state.audio[i+1]=speak(st.session_state.history[-1]["content"])
                    st.session_state.q_index+=1
                    st.rerun()
                else:
                    st.warning("Please answer this question first.")

            
        else:
            if st.button("Submit Interview"):
                if len(st.session_state.answers)== total:
                    st.session_state.interview_submitted=True
                    # the end of the time :
                    st.session_state.endtime=round((time.time()-st.session_state.start_time)/60, 1)
                    result=evaluate_answer([m["content"] for m in st.session_state.history if m["role"]=="assistant"],st.session_state.answers)



                    # evaluation::
                    st.subheader("Interview Evaluation")
                    st.write("Total time (minutes):", st.session_state.endtime)
                    c1,c2,c3=st.columns(3)
                    c1.metric("Clarity", f"{result['clarity']}/10")
                    c2.metric("Confidence", f"{result['confidence']}/10")
                    c3.metric("Relevance", f"{result['relevance']}/10")
                    st.subheader("Overall Feedback")
                    st.markdown('<div class="jobcard">'+result["feedback"]+'</div>', unsafe_allow_html=True)
                    
                else:
                    st.warning("Please answer all 5 questions first.")



with tab3:
    if uploaded_file is None:
        st.info("Upload your CV first !😁")
    else:
        if st.button("Get CV feedback"):
            open(uploaded_file.name,"wb").write(uploaded_file.getvalue())
            # cv_text : data from upload file by using read function , feedback : use feedback fuction and save them , suggestions :if there is , 
            st.session_state.cv_text=read_cv(uploaded_file.name)
            st.session_state.feedback=cv_feedback(st.session_state.cv_text)
            st.session_state.suggestions=None


            
        if "feedback" in st.session_state:
            # write the feedbaack :
            st.markdown(st.session_state.feedback)
            # if the user want to edit the cv :
            if st.button("Suggest edits"):
                # try and expect for avoid error (limit), use cv_suggestions function and show each suggestion :
                try:
                    st.session_state.suggestions=cv_suggestions(st.session_state.cv_text)
                    for k in range(10):
                        st.session_state[f"acc{k}"]=False
                except Exception:
                    st.error("The AI service is busy.Please wait a minute and press the button again😥.")

        # the split part < for each section for each label        
        if st.session_state.get("suggestions"):
            lines=[]
            # split the cv 
            for line in st.session_state.cv_text.split("\n"):
                t=line.strip()
                # the titles , captil letters 
                if t and t.isupper() and len(t)<40 and not any(c.isdigit() for c in t):
                    # for make them bold words
                    lines.append("\n\n**"+t+"**\n\n")
                elif t:
                    lines.append(t)
            ## create new cv 
            cv=" ".join(lines)
            found=[]
            # for loop for put the suggestion in the cv, contains (original, suggestion , reason ) 
            for n,s in enumerate(st.session_state.suggestions):
                # old sentence , put split to avoid spaces
                o=" ".join(s["original"].split())
                #find the sentence in the cv
                if cv.find(o)!=-1:
                    found.append((cv.find(o),n,o))


            found.sort()
            # all edits that accept will add it in this list
            edits= []

            # 3 varibles the position in the cv , and the index of this suggestion , and the text
            for pos,n,o in found:
                # if the user accept the edit :
                if st.session_state.get(f"acc{n}"):
                    edits.append((o, st.session_state.suggestions[n]["suggestion"]))

                    


            # downloads the new cv , after using apply edits function
            if uploaded_file.name.endswith(".docx"):
                path=apply_edits(uploaded_file.name, edits)
                # choose rb 
                st.download_button("Download edited CV", open(path,"rb").read(),file_name="edited_cv.docx")
            else:
                # if the user upload pdf , to edit this cv , convert it to docx 
                try:
                    covt=Converter(uploaded_file.name)
                    covt.convert("converted_cv.docx")
                    covt.close()
                    # then apply the edits 
                    path=apply_edits("converted_cv.docx",edits)
                except Exception:
                    path=plain_docx(cv, edits)
                st.download_button("Download edited CV",open(path,"rb").read(),file_name="edited_cv.docx")




                # make the paper of the cv :
            st.markdown('<style>.st-key-paper{background:white;border:1px solid #DDE3EE;border-radius:12px;padding:28px 34px;box-shadow:0 2px 8px rgba(31,58,104,0.12)}</style>', unsafe_allow_html=True)


            # container: a box that holds everything inside it ;
            with st.container(key="paper"):

                # split the cv then take the last one to conitnue
                last=0

                
                for i,n,o in found:
                    if i<last:
                        continue

                    #delete the last scape 
                    segment=cv[last:i].rstrip()
                    
                    if segment.endswith("●"):
                        # to delete the point , and write next time
                        segment=segment[:-1].rstrip()
                    #for each point a line 
                    st.write(segment.replace("●", "\n\n●"))

                    # suggestions list, 
                    s=st.session_state.suggestions[n]
                    old_text=("● " if o.startswith("●") else "")+o.replace("●", "").strip()
                    new_text=("● " if o.startswith("●") else "")+s["suggestion"].replace("●", "").strip()


                    
                    if st.session_state.get(f"acc{n}"):
                        # 
                        st.markdown('<div style="text-decoration:line-through;color:#8A94A6">'+old_text+'</div>', unsafe_allow_html=True)
                        st.write(new_text)
                    else:
                        # I put the old text ,then the user can compare which  test is the best 
                        st.write(old_text)
                        #the green box of the suggest text
                        st.markdown('<div style="font-size:13.5px;color:#1F5C3E;background:#F1F8F4;border-left:4px solid #1F7A4D;padding:9px 13px;border-radius:4px">'+s["suggestion"].replace("●", "").strip()+'<div style="font-size:12px;color:#5B667A;margin-top:3px">'+s["reason"]+'</div></div>', unsafe_allow_html=True)
                        # if the user click accept 
                        if st.button("Accept this edit", key=f"btn{n}"):
                            # save that the edis is acceot by user 
                            st.session_state[f"acc{n}"]=True
                            st.rerun()
                    last=i+len(o)

                    # put - to the old sentences 
                st.write(cv[last:].replace("●", "\n\n●"))
