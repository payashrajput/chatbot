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

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Payash AI ChatBox",
    page_icon="🤖",
    layout="wide"
)

# --------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------

st.markdown("""
<style>

.main {
    background-color: #0e1117;
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
# TITLE
# --------------------------------------------------

st.markdown(
    '<div class="title">🤖 Payash AI ChatBox</div>',
    unsafe_allow_html=True
)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

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

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.1
    )

    max_new_tokens = st.slider(
        "Max Tokens",
        min_value=128,
        max_value=4096,
        value=1024
    )

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --------------------------------------------------
# LOAD MODEL
# --------------------------------------------------

@st.cache_resource(show_spinner=False)
def load_model(repo_id, temp, max_tokens):

    llm = HuggingFaceEndpoint(
        repo_id=repo_id,
        task="text-generation",
        temperature=temp,
        max_new_tokens=max_tokens
    )

    return ChatHuggingFace(llm=llm)

model = load_model(
    model_name,
    temperature,
    max_new_tokens
)

# --------------------------------------------------
# CHAT MEMORY
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# --------------------------------------------------
# DISPLAY CHAT HISTORY
# --------------------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --------------------------------------------------
# CHAT INPUT
# --------------------------------------------------

prompt = st.chat_input("Ask me anything...")

if prompt:

    # Save user message

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # --------------------------------------------------
    # BUILD CONVERSATION HISTORY
    # --------------------------------------------------

    conversation = [
        SystemMessage(
            content="""
You are Payash AI.

You are a helpful, intelligent, and friendly assistant.

Always use previous messages in the conversation
to answer follow-up questions.
"""
        )
    ]

    for msg in st.session_state.messages:

        if msg["role"] == "user":

            conversation.append(
                HumanMessage(
                    content=msg["content"]
                )
            )

        elif msg["role"] == "assistant":

            conversation.append(
                AIMessage(
                    content=msg["content"]
                )
            )

    # --------------------------------------------------
    # GENERATE RESPONSE
    # --------------------------------------------------

    with st.chat_message("assistant"):

        placeholder = st.empty()
        placeholder.markdown("⏳ Thinking...")

        try:

            response = model.invoke(conversation)

            if hasattr(response, "content"):
                answer = response.content
            else:
                answer = str(response)

            typed_text = ""

            for char in answer:

                typed_text += char

                placeholder.markdown(
                    typed_text
                )

                time.sleep(0.002)

        except Exception as e:

            answer = f"❌ Error: {str(e)}"
            placeholder.error(answer)

    # --------------------------------------------------
    # SAVE ASSISTANT MESSAGE
    # --------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
