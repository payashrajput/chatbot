import os
import time
import streamlit as st

from langchain_huggingface import (
    HuggingFaceEndpoint,
    ChatHuggingFace
)

# --------------------------------------------------
# Page Config
# --------------------------------------------------

st.set_page_config(
    page_title="Payash's Chatbot",
    page_icon="🤖",
    layout="wide"
)

# --------------------------------------------------
# Custom CSS
# --------------------------------------------------

st.markdown("""
<style>

.main {
    background-color: #0e1117;
}

.stChatMessage {
    border-radius: 15px;
    padding: 10px;
}

.user-msg {
    background: #1f6feb;
    padding: 12px;
    border-radius: 15px;
    color: white;
}

.bot-msg {
    background: #262730;
    padding: 12px;
    border-radius: 15px;
    color: white;
}

.title {
    text-align:center;
    font-size:40px;
    font-weight:bold;
    background: linear-gradient(90deg,#00d4ff,#7d5fff);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Title
# --------------------------------------------------

st.markdown(
    '<div class="title">🤖 Payash personal Assistant</div>',
    unsafe_allow_html=True
)

# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:
    st.title("⚙ Settings")

    temperature = st.slider(
        "Temperature",
        0.0,
        2.0,
        1.5,
        0.1
    )

    max_new_tokens = st.slider(
        "Max Tokens",
        128,
        4096,
        1024
    )

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --------------------------------------------------
# LLM
# --------------------------------------------------

@st.cache_resource
def load_model(temp, max_tokens):

    llm = HuggingFaceEndpoint(
        repo_id="deepseek-ai/DeepSeek-V4-Pro",
        task="text-generation",
        temperature=temp,
        max_new_tokens=max_tokens
    )

    model = ChatHuggingFace(
        llm=llm,
        temperature=temp
    )

    return model

model = load_model(
    temperature,
    max_new_tokens
)

# --------------------------------------------------
# Chat Memory
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# --------------------------------------------------
# Display History
# --------------------------------------------------

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --------------------------------------------------
# User Input
# --------------------------------------------------

prompt = st.chat_input(
    "Ask me anything..."
)

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        placeholder = st.empty()

        placeholder.markdown("⏳ Thinking...")

        try:

            response = model.invoke(prompt)

            answer = response.content

            typed_text = ""

            for char in answer:
                typed_text += char
                placeholder.markdown(typed_text)
                time.sleep(0.005)

        except Exception as e:

            answer = f"Error: {str(e)}"
            placeholder.error(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
