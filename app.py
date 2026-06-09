import os
import time
import streamlit as st
from langchain_huggingface import HuggingFaceEndpoint
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

st.set_page_config(
    page_title="Payash's Chatbot",
    page_icon="🤖",
    layout="wide"
)

st.markdown("""
<style>
.main { background-color: #0e1117; }
.stChatMessage { border-radius: 15px; padding: 10px; }
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
    text-align: center;
    font-size: 40px;
    font-weight: bold;
    background: linear-gradient(90deg, #00d4ff, #7d5fff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="title">🤖 Payash Personal Assistant</div>',
    unsafe_allow_html=True
)

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
if not HF_TOKEN:
    st.error("HUGGINGFACEHUB_API_TOKEN not found. Add it in Streamlit Secrets.")
    st.stop()

with st.sidebar:
    st.title("⚙ Settings")
    temperature = st.slider("Temperature", 0.1, 2.0, 0.7, 0.1)
    max_tokens = st.slider("Max Tokens", 128, 2048, 512)
    model_choice = st.selectbox(
        "Choose Model",
        [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "microsoft/Phi-3-mini-4k-instruct",
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        ]
    )
    st.divider()
    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    st.markdown("**Messages:** " + str(len(st.session_state.get("messages", []))))

TEMPLATE = (
    "You are Payash, a smart and friendly personal assistant. "
    "Answer clearly and helpfully.\n\n"
    "Conversation History:\n{history}\n\n"
    "User: {input}\n"
    "Assistant:"
)

prompt_template = PromptTemplate(
    input_variables=["history", "input"],
    template=TEMPLATE
)

@st.cache_resource
def load_model(repo_id, temp, max_new_tokens):
    llm = HuggingFaceEndpoint(
        repo_id=repo_id,
        task="text-generation",
        huggingfacehub_api_token=HF_TOKEN,
        temperature=temp,
        max_new_tokens=max_new_tokens,
        do_sample=True
    )
    return LLMChain(llm=llm, prompt=prompt_template)

try:
    chain = load_model(model_choice, temperature, max_tokens)
except Exception as e:
    st.error(f"Model loading failed: {e}")
    st.stop()

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
        placeholder.markdown("⏳ Thinking...")

        try:
            history_str = ""
            for msg in st.session_state.messages[:-1]:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_str += f"{role}: {msg['content']}\n"

            response = chain.invoke({
                "history": history_str,
                "input": prompt
            })

            answer = response.get("text", "").strip()

            if "Assistant:" in answer:
                answer = answer.split("Assistant:")[-1].strip()

            typed_text = ""
            for char in answer:
                typed_text += char
                placeholder.markdown(typed_text)
                time.sleep(0.005)

        except Exception as e:
            answer = f"Error: {str(e)}"
            placeholder.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
