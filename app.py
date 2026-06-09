import os
import time
import requests
import streamlit as st

st.set_page_config(
    page_title="Payash Personal Assistant",
    page_icon="🤖",
    layout="wide"
)

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
if not HF_TOKEN:
    st.error("HUGGINGFACEHUB_API_TOKEN not found. Add it in Render Environment Variables.")
    st.stop()

st.markdown("""
<style>
.stApp { background-color: #0e1117; }
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

st.markdown('<div class="title">🤖 Payash Personal Assistant</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙ Settings")
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
    max_tokens = st.slider("Max Tokens", 128, 2048, 512)
    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

def query_model(prompt, temperature, max_tokens):
    API_URL = "https://api-inference.huggingface.co/models/TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "temperature": temperature,
            "max_new_tokens": max_tokens,
            "return_full_text": False
        }
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    result = response.json()

    if isinstance(result, list) and len(result) > 0:
        return result[0].get("generated_text", "No response received.")
    elif isinstance(result, dict) and "error" in result:
        return f"API Error: {result['error']}"
    else:
        return str(result)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Ask me anything...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            placeholder.markdown("⏳ Thinking...")

            history_text = ""
            for msg in st.session_state.messages[:-1]:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n"

            full_prompt = f"{history_text}User: {prompt}\nAssistant:"

            answer = query_model(full_prompt, temperature, max_tokens)

            text = ""
            for ch in answer:
                text += ch
                placeholder.markdown(text)
                time.sleep(0.002)

        except Exception as e:
            answer = f"❌ Error: {e}"
            placeholder.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
