import os
import json
import time
import streamlit as st

from langchain_huggingface import (
    HuggingFaceEndpoint,
    ChatHuggingFace
)

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage
)

# ==================================================
# CONFIG
# ==================================================

st.set_page_config(
    page_title="KITTU AI",
    page_icon="🤖",
    layout="wide"
)

# ==================================================
# SIMPLE LOGIN (SAFE VERSION)
# ==================================================
# (Replace later with Google OAuth if needed)

def login():
    st.sidebar.title("🔐 Login")

    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state["logged_in"] = True
            st.session_state["user"] = username
        else:
            st.sidebar.error("Invalid credentials")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

# ==================================================
# APP TITLE
# ==================================================

st.markdown(
    """
    <div style="text-align:center;font-size:42px;
    font-weight:bold;
    background: linear-gradient(90deg,#00d4ff,#7d5fff);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;">
    🤖 KITTU AI
    </div>
    """,
    unsafe_allow_html=True
)

# ==================================================
# HISTORY
# ==================================================

HISTORY_FILE = "chat_history.json"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:

    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                st.session_state.chat_history = json.load(f)
        except:
            st.session_state.chat_history = []
    else:
        st.session_state.chat_history = []

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.chat_history, f, indent=2)

# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.title("⚙ Settings")

    model_name = st.selectbox(
        "Choose Model",
        [
            "deepseek-ai/DeepSeek-V4-Pro",
            "meta-llama/Llama-3.1-8B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3"
        ]
    )

    temperature = st.slider("Temperature", 0.0, 2.0, 1.0, 0.1)
    max_new_tokens = st.slider("Max Tokens", 128, 4096, 1024)

    st.divider()

    st.success(f"Logged in as {st.session_state.get('user')}")

    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.subheader("📜 Chat History")

    for i, chat in enumerate(reversed(st.session_state.chat_history)):
        if st.button(chat["title"], key=i):
            st.session_state.messages = chat["messages"]
            st.rerun()

# ==================================================
# MODEL
# ==================================================

@st.cache_resource(show_spinner=False)
def load_model(repo_id, temperature, max_new_tokens):

    llm = HuggingFaceEndpoint(
        repo_id=repo_id,
        task="text-generation",
        temperature=temperature,
        max_new_tokens=max_new_tokens
    )

    return ChatHuggingFace(llm=llm)

model = load_model(model_name, temperature, max_new_tokens)

# ==================================================
# CHAT DISPLAY
# ==================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==================================================
# INPUT
# ==================================================

prompt = st.chat_input("Ask me anything...")

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

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

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
