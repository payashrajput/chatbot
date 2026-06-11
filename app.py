import os
import json
import time
import streamlit as st

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ==================================================
# CONFIG
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

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ==================================================
# SAFE HISTORY FILE
# ==================================================

HISTORY_FILE = "chat_history.json"

# Load history safely
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                st.session_state.chat_history = data
    except:
        st.session_state.chat_history = []

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.chat_history, f, indent=2)

# ==================================================
# SIDEBAR SETTINGS
# ==================================================

with st.sidebar:

    st.header("⚙ Settings")

    model_name = st.selectbox(
        "Choose Model",
        [
            "microsoft/Phi-3-mini-4k-instruct",
            "HuggingFaceH4/zephyr-7b-beta"
        ]
    )

    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
    max_tokens = st.slider("Max Tokens", 128, 2048, 1024)

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.subheader("📜 Chat History")

    # SAFE HISTORY DISPLAY (NO KEYERROR)
    for i, chat in enumerate(reversed(st.session_state.chat_history)):

        title = chat.get("title", "New Chat")

        if st.button(f"💬 {title}", key=str(i)):
            st.session_state.messages = chat.get("messages", [])
            st.rerun()

# ==================================================
# MODEL LOADER
# ==================================================

@st.cache_resource(show_spinner=False)
def load_model(repo_id, temperature, max_tokens):

    llm = HuggingFaceEndpoint(
        repo_id=repo_id,
        task="text-generation",
        temperature=temperature,
        max_new_tokens=max_tokens
    )

    return ChatHuggingFace(llm=llm)

model = load_model(model_name, temperature, max_tokens)

# ==================================================
# DISPLAY CHAT
# ==================================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==================================================
# INPUT
# ==================================================

prompt = st.chat_input("Ask me anything...")

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    conversation = [
        SystemMessage(content="You are KITTU AI, a helpful assistant.")
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

            text = ""
            for c in answer:
                text += c
                placeholder.markdown(text)
                time.sleep(0.002)

        except Exception as e:
            answer = f"❌ Error: {e}"
            placeholder.error(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    # SAVE CHAT WITH SAFE TITLE
    first_user = "New Chat"
    for m in st.session_state.messages:
        if m["role"] == "user":
            first_user = m["content"][:50]
            break

    st.session_state.chat_history.append({
        "title": first_user,
        "messages": st.session_state.messages.copy()
    })

    save_history()
