import os
import streamlit as st
import time

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ==================================================
# LOAD HF TOKEN (GIT SAFE)
# ==================================================

HF_TOKEN = st.secrets.get("HUGGINGFACEHUB_API_TOKEN")

if not HF_TOKEN:
    st.error("❌ Missing Hugging Face API token in Streamlit Secrets")
    st.stop()

os.environ["HUGGINGFACEHUB_API_TOKEN"] = HF_TOKEN

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="KITTU AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 KITTU AI (HF + DeepSeek)")

# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:
    st.header("⚙ Settings")

    model_choice = st.selectbox(
        "Choose Model Type",
        [
            "HuggingFace - Phi-3 Mini",
            "HuggingFace - Zephyr 7B",
            "DeepSeek (via HF)",
        ]
    )

    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
    max_tokens = st.slider("Max Tokens", 128, 2048, 1024)

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ==================================================
# MODEL MAP
# ==================================================

def get_model(model_choice):
    if model_choice == "HuggingFace - Phi-3 Mini":
        return "microsoft/Phi-3-mini-4k-instruct"

    elif model_choice == "HuggingFace - Zephyr 7B":
        return "HuggingFaceH4/zephyr-7b-beta"

    elif model_choice == "DeepSeek (via HF)":
        # IMPORTANT: HF hosted DeepSeek model
        return "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"

# ==================================================
# SESSION STATE
# ==================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==================================================
# LOAD MODEL
# ==================================================

@st.cache_resource
def load_model(repo_id, temperature, max_tokens):

    llm = HuggingFaceEndpoint(
        repo_id=repo_id,
        task="text-generation",
        huggingfacehub_api_token=os.environ["HUGGINGFACEHUB_API_TOKEN"],
        temperature=temperature,
        max_new_tokens=max_tokens
    )

    return ChatHuggingFace(llm=llm)

model_name = get_model(model_choice)
model = load_model(model_name, temperature, max_tokens)

# ==================================================
# CHAT DISPLAY
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
        SystemMessage(content="You are KITTU AI, a smart helpful assistant.")
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

            typed = ""
            for c in answer:
                typed += c
                placeholder.markdown(typed)
                time.sleep(0.002)

        except Exception as e:
            answer = f"❌ Error: {e}"
            placeholder.error(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
