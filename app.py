import streamlit as st
import time

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="KITTU AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 KITTU AI")

# ==================================================
# SESSION STATE
# ==================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==================================================
# MODEL (STABLE)
# ==================================================

@st.cache_resource
def load_model():
    return ChatHuggingFace(
        llm=HuggingFaceEndpoint(
            repo_id="microsoft/Phi-3-mini-4k-instruct",
            task="text-generation",
            temperature=0.7,
            max_new_tokens=1024
        )
    )

model = load_model()

# ==================================================
# SHOW CHAT HISTORY
# ==================================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==================================================
# USER INPUT
# ==================================================

prompt = st.chat_input("Ask me anything...")

if prompt:

    # save user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    # build conversation
    conversation = [
        SystemMessage(content="You are KITTU AI, a helpful assistant.")
    ]

    for m in st.session_state.messages:
        if m["role"] == "user":
            conversation.append(HumanMessage(content=m["content"]))
        else:
            conversation.append(AIMessage(content=m["content"]))

    # assistant response
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

    # save assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import json
import os
import time

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ==================================================
# CONFIG
# ==================================================

st.set_page_config(page_title="KITTU AI PRO", page_icon="🤖", layout="wide")

# ==================================================
# AUTH
# ==================================================

with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"]
)

authenticator.login()

if st.session_state.get("authentication_status") is False:
    st.error("❌ Wrong login")
    st.stop()

if st.session_state.get("authentication_status") is None:
    st.warning("🔐 Login required")
    st.stop()

authenticator.logout("Logout", "sidebar")

st.sidebar.success(f"Welcome {st.session_state['name']}")

# ==================================================
# MODEL (FIXED + STABLE CHAT MODEL)
# ==================================================

@st.cache_resource
def load_model():
    return ChatHuggingFace(
        llm=HuggingFaceEndpoint(
            repo_id="HuggingFaceH4/zephyr-7b-beta",
            task="text-generation",
            temperature=0.7,
            max_new_tokens=1024
        )
    )

model = load_model()

# ==================================================
# MEMORY
# ==================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

HISTORY_FILE = "chat_history.json"

def save_history():
    with open(HISTORY_FILE, "w") as f:
        json.dump(st.session_state.messages, f, indent=2)

# ==================================================
# SIDEBAR CONTROLS
# ==================================================

with st.sidebar:
    st.title("⚙ Controls")

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ==================================================
# UI HEADER
# ==================================================

st.title("🤖 KITTU AI PRO")

# ==================================================
# DISPLAY CHAT
# ==================================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==================================================
# INPUT
# ==================================================

prompt = st.chat_input("Ask anything...")

if prompt:

    st.session_state.messages.append({"role": "user", "content": prompt})

    conversation = [
        SystemMessage(content="You are KITTU AI. Be helpful, smart, and concise.")
    ]

    for m in st.session_state.messages:
        if m["role"] == "user":
            conversation.append(HumanMessage(content=m["content"]))
        else:
            conversation.append(AIMessage(content=m["content"]))

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ Thinking...")

        try:
            response = model.invoke(conversation)
            answer = response.content

            # STREAMING EFFECT (FAST UX)
            text = ""
            for c in answer:
                text += c
                placeholder.markdown(text)
                time.sleep(0.002)

        except Exception as e:
            answer = f"Error: {e}"
            placeholder.error(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    save_history()
