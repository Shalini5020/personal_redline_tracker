from google import genai
from google.genai import types 
import streamlit as st 
import requests
from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE, SUMMARY_REQUEST_PROMPT

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)

gemini_client = get_gemini_client()
MODEL_NAME = "gemini-3.5-flash"

def send_telegram_summary(summary_text):
    url = f"https://telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": summary_text
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            st.success("🚀 Summary successfully sent to Telegram!")
        else:
            st.error(f"Telegram failed: {response.text}")
    except Exception as e:
        st.error(f"An error occurred: {e}")

if "onboarded" not in st.session_state:
    st.title("📚 AI Deadline Tracker")
    st.caption("Upload your syllabus or timetable. Get reminders directly on Telegram.")
    
    with st.form("onboarding_form"):
        name = st.text_input("Your Name")
        submitted = st.form_submit_button("Get Started 🚀")
        
    if submitted:
        if not name.strip():
            st.warning("Please enter your name to proceed.")
        else:
            st.session_state.name = name.strip()
            st.session_state.chat = gemini_client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            st.session_state.messages = []
            st.session_state.onboarded = True
            st.rerun()
    st.stop()

def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])
 
def add_message(role, kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])
 
if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)

def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(parts).text
    except Exception as error:
        return f"Sorry, something went wrong: {error}"

user_input = st.chat_input(
    "Ask a question, or attach a photo of your schedule",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)
 
if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts = []
 
    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    
    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append(SUMMARY_REQUEST_PROMPT)
 
    with st.spinner("Analyzing document..."):
        answer = ask_gemini(parts)
    
    add_message("assistant", "text", answer)
    
    with st.spinner("Sending to Telegram..."):
        send_telegram_summary(answer)
