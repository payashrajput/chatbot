import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os
import json
import time

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(page_title="KITTU AI", page_icon="🤖", layout="wide")

# ==================================================
# LOAD AUTH CONFIG
# ==================================================

with open("config.yaml", "r") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"]
)

authenticator.login()

# ==================================================
# LOGIN CHECK
# ==================================================

if st.session_state.get("authentication_status") is False:
    st.error("❌ Wrong username or password")
    st.stop()

if st.session_state.get("authentication_status") is None:
    st.warning("🔐 Please login to continue")
    st.stop()

# Logged in
authenticator.logout("Logout", "sidebar")
st.sidebar.success(f"Welcome {st.session_state['name']}")

# ==================================================
# CHAT HISTORY
# ==================================================

HISTORY_FILE = "chat_history.json"

if "messages" not in st.session_state:
    st.session_state.messages = []

if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r") as f:
            st.session_state.chat_history = json.load(f)
    except:
        st.session_state.chat_history = []
else:
    st.session_state.chat_history = []

def save_history():
    with open(HISTORY_FILE, "w") as f:
        json.dump(st.session_state.chat_history, f, indent=2)

# ==================================================
# MODEL
# ==================================================

@st.cache_resource
def load_model():
    return ChatHuggingFace(
        llm=HuggingFaceEndpoint(
            repo_id="mistralai/Mistral-7B-Instruct-v0.3",
            task="text-generation",
            temperature=0.7,
            max_new_tokens=1024
        )
    )

model = load_model()

# ==================================================
# UI
# ==================================================

st.title("🤖 KITTU AI")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==================================================
# INPUT
# ==================================================

prompt = st.chat_input("Ask me anything...")

if prompt:

    st.session_state.messages.append({"role": "user", "content": prompt})

    conversation = [
        SystemMessage(content="You are KITTU AI, a helpful assistant.")
    ]

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            conversation.append(HumanMessage(content=msg["content"]))
        else:
            conversation.append(AIMessage(content=msg["content"]))

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ Thinking...")

        try:
            response = model.invoke(conversation)
            answer = response.content

            typed = ""
            for c in answer:
                typed += c
                placeholder.markdown(typed)
                time.sleep(0.002)

        except Exception as e:
            answer = f"Error: {e}"
            placeholder.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
