import os
import time
import streamlit as st
from langchain_huggingface import HuggingFaceEndpoint

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
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
    max_tokens = st.slider("Max Tokens", 128, 2048, 512)
    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ----------------------------------
# MODEL
# ----------------------------------
@st.cache_resource
def load_model(temp, max_new_tokens):
    return HuggingFaceEndpoint(
        repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        task="conversational",              # ✅ fixed task
        huggingfacehub_api_token=HF_TOKEN,
        temperature=temp,
        max_new_tokens=max_new_tokens
    )

try:
    model = load_model(temperature, max_tokens)
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
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            placeholder.markdown("⏳ Thinking...")

            # Build conversation context
            history_text = ""
            for msg in st.session_state.messages[:-1]:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n"

            full_prompt = f"{history_text}User: {prompt}\nAssistant:"

            # Invoke model
            answer = model.invoke(full_prompt)

            # HuggingFaceEndpoint may return dict or string
            if isinstance(answer, dict):
                answer = answer.get("generated_text") or answer.get("text") or str(answer)

            # Clean echoed prompt if present
            if "Assistant:" in answer:
                answer = answer.split("Assistant:")[-1].strip()

            # Typewriter effect
            text = ""
            for ch in answer:
                text += ch
                placeholder.markdown(text)
                time.sleep(0.002)

        except Exception as e:
            answer = f"❌ Error: {e}"
            placeholder.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})import os
import time
import streamlit as st
from langchain_huggingface import HuggingFaceEndpoint

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
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
    max_tokens = st.slider("Max Tokens", 128, 2048, 512)
    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ----------------------------------
# MODEL
# ----------------------------------
@st.cache_resource
def load_model(temp, max_new_tokens):
    return HuggingFaceEndpoint(
        repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        task="text-generation",
        huggingfacehub_api_token=HF_TOKEN,
        temperature=temp,
        max_new_tokens=max_new_tokens
    )

try:
    model = load_model(temperature, max_tokens)
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
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            placeholder.markdown("⏳ Thinking...")

            # Build conversation context from history
            history_text = ""
            for msg in st.session_state.messages[:-1]:  # exclude current prompt
                role = "User" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n"

            full_prompt = f"{history_text}User: {prompt}\nAssistant:"

            # Invoke model — returns plain string
            answer = model.invoke(full_prompt)

            # Clean up if model echoes the prompt
            if "Assistant:" in answer:
                answer = answer.split("Assistant:")[-1].strip()

            # Typewriter effect
            text = ""
            for ch in answer:
                text += ch
                placeholder.markdown(text)
                time.sleep(0.002)

        except Exception as e:
            answer = f"❌ Error: {e}"
            placeholder.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
