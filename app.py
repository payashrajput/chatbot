import os
import time
import streamlit as st

from langchain_huggingface import (
    HuggingFaceEndpoint,
    ChatHuggingFace
)

# ----------------------------------
# PAGE CONFIG
# ----------------------------------

st.set_page_config(
    page_title="Payash Personal Assistant",
    page_icon="🤖",
    layout="wide"
)

# ----------------------------------
# TOKEN CHECK
# ----------------------------------

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

if not HF_TOKEN:
    st.error(
        "HUGGINGFACEHUB_API_TOKEN not found.\n\n"
        "Add it in Render Environment Variables."
    )
    st.stop()

# ----------------------------------
# CUSTOM CSS
# ----------------------------------

st.markdown("""
<style>

.stApp {
    background-color: #0e1117;
}

.title {
    text-align: center;
    font-size: 42px;
    font-weight: bold;
    background: linear-gradient(90deg,#00d4ff,#7d5fff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 20px;
}

</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="title">🤖 Payash Personal Assistant</div>',
    unsafe_allow_html=True
)

# ----------------------------------
# SIDEBAR
# ----------------------------------

with st.sidebar:

    st.header("⚙ Settings")

    temperature = st.slider(
        "Temperature",
        0.0,
        2.0,
        0.7,
        0.1
    )

    max_tokens = st.slider(
        "Max Tokens",
        128,
        2048,
        512
    )

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ----------------------------------
# MODEL
# ----------------------------------

@st.cache_resource
def load_model(temp, max_new_tokens):

    llm = HuggingFaceEndpoint(
        repo_id="HuggingFaceH4/zephyr-7b-beta",
        task="text-generation",
        huggingfacehub_api_token=HF_TOKEN,
        temperature=temp,
        max_new_tokens=max_new_tokens
    )

    return ChatHuggingFace(llm=llm)

try:
    model = load_model(
        temperature,
        max_tokens
    )

except Exception as e:
    st.error(f"Model loading failed:\n\n{e}")
    st.stop()

# ----------------------------------
# CHAT HISTORY
# ----------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# ----------------------------------
# DISPLAY HISTORY
# ----------------------------------

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ----------------------------------
# USER INPUT
# ----------------------------------

prompt = st.chat_input("Ask me anything...")

if prompt:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        placeholder = st.empty()

        try:

            placeholder.markdown("⏳ Thinking...")

            response = model.invoke(prompt)

            answer = response.content

            text = ""

            for ch in answer:
                text += ch
                placeholder.markdown(text)
                time.sleep(0.002)

        except Exception as e:

            answer = f"❌ Error: {e}"
            placeholder.error(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
