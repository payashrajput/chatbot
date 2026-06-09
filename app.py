import os
import time
import anthropic
import streamlit as st

st.set_page_config(
    page_title="Payash Personal Assistant",
    page_icon="🤖",
    layout="wide"
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    st.error("ANTHROPIC_API_KEY not found. Add it in Render Environment Variables.")
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
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    max_tokens = st.slider("Max Tokens", 128, 2048, 512)
    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                temperature=temperature,
                system="You are Payash, a helpful personal assistant. Be concise and friendly.",
                messages=st.session_state.messages
            )

            answer = response.content[0].text

            text = ""
            for ch in answer:
                text += ch
                placeholder.markdown(text)
                time.sleep(0.002)

        except Exception as e:
            answer = f"❌ Error: {e}"
            placeholder.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
