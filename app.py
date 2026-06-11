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
# HISTORY FILE
# ==================================================

HISTORY_FILE = "chat_history.json"

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

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.subheader("📜 Chat History")

    for i, chat in enumerate(reversed(st.session_state.chat_history)):
        title = chat.get("title", "New Chat")

        if st.button(f"💬 {title}", key=f"history_{i}"):
            st.session_state.messages = chat.get("messages", [])
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
# SHOW CHAT HISTORY
# ==================================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==================================================
# INPUT (FIXED FLOW - IMPORTANT PART)
# ==================================================

prompt = st.chat_input("Ask me anything...")

if prompt:

    # 1. Save user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    # 2. SHOW USER MESSAGE INSTANTLY (FIX FOR YOUR ISSUE)
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. Build conversation
    conversation = [
        SystemMessage(content="You are KITTU AI, a helpful assistant.")
    ]

    for m in st.session_state.messages:
        if m["role"] == "user":
            conversation.append(HumanMessage(content=m["content"]))
        else:
            conversation.append(AIMessage(content=m["content"]))

    # 4. AI RESPONSE
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
            answer = f"❌ Error: {e}"
            placeholder.error(answer)

    # 5. SAVE AI MESSAGE
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    # 6. SAVE HISTORY SAFELY
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
