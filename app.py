import os
import json
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

# ==================================================
# CONFIG
# ==================================================

st.set_page_config(
    page_title="KITTU AI",
    page_icon="🤖",
    layout="wide"
)

HISTORY_FILE = "chat_history.json"

# ==================================================
# CSS
# ==================================================

st.markdown("""
<style>

.main {
    background-color: #0e1117;
}

.title {
    text-align:center;
    font-size:42px;
    font-weight:bold;
    background: linear-gradient(90deg,#00d4ff,#7d5fff);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    margin-bottom:20px;
}

</style>
""", unsafe_allow_html=True)

# ==================================================
# TITLE
# ==================================================

st.markdown(
    '<div class="title">🤖 KITTU AI</div>',
    unsafe_allow_html=True
)

# ==================================================
# SESSION STATE
# ==================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:

    if os.path.exists(HISTORY_FILE):

        try:
            with open(
                HISTORY_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                st.session_state.chat_history = json.load(f)

        except Exception:
            st.session_state.chat_history = []

    else:
        st.session_state.chat_history = []

# ==================================================
# SAVE HISTORY
# ==================================================

def save_history():

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            st.session_state.chat_history,
            f,
            indent=2,
            ensure_ascii=False
        )

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

    temperature = st.slider(
        "Temperature",
        0.0,
        2.0,
        1.0,
        0.1
    )

    max_new_tokens = st.slider(
        "Max Tokens",
        128,
        4096,
        1024
    )

    # --------------------------------------------
    # Clear Chat
    # --------------------------------------------

    if st.button("🗑 Clear Chat"):

        if st.session_state.messages:

            first_user_msg = "New Chat"

            for msg in st.session_state.messages:

                if msg["role"] == "user":

                    first_user_msg = (
                        msg["content"]
                        .replace("\n", " ")
                        [:50]
                    )

                    break

            st.session_state.chat_history.append(
                {
                    "title": first_user_msg,
                    "messages":
                        st.session_state.messages.copy()
                }
            )

            save_history()

        st.session_state.messages = []

        st.rerun()

    st.divider()

    st.subheader("📜 Chat History")

    if not st.session_state.chat_history:

        st.caption("No saved chats yet.")

    else:

        for idx, chat in enumerate(
            reversed(
                st.session_state.chat_history
            )
        ):

            if st.button(
                f"💬 {chat['title']}",
                key=f"history_{idx}"
            ):

                st.session_state.messages = (
                    chat["messages"].copy()
                )

                st.rerun()

# ==================================================
# MODEL
# ==================================================

@st.cache_resource(show_spinner=False)
def load_model(
    repo_id,
    temperature,
    max_new_tokens
):

    llm = HuggingFaceEndpoint(
        repo_id=repo_id,
        task="text-generation",
        temperature=temperature,
        max_new_tokens=max_new_tokens
    )

    return ChatHuggingFace(llm=llm)

model = load_model(
    model_name,
    temperature,
    max_new_tokens
)

# ==================================================
# DISPLAY CHAT
# ==================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):
        st.markdown(
            message["content"]
        )

# ==================================================
# USER INPUT
# ==================================================

prompt = st.chat_input(
    "Ask me anything..."
)

if prompt:

    # ------------------------------------------
    # Save User Message
    # ------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # ------------------------------------------
    # Build Conversation
    # ------------------------------------------

    conversation = [

        SystemMessage(
            content="""
You are Payash AI.

You are a helpful AI assistant.

Remember previous messages and
answer follow-up questions using
conversation history.
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

        else:

            conversation.append(
                AIMessage(
                    content=msg["content"]
                )
            )

    # ------------------------------------------
    # Generate Response
    # ------------------------------------------

    with st.chat_message(
        "assistant"
    ):

        placeholder = st.empty()

        placeholder.markdown(
            "⏳ Thinking..."
        )

        try:

            response = model.invoke(
                conversation
            )

            answer = (
                response.content
                if hasattr(
                    response,
                    "content"
                )
                else str(response)
            )

            typed_text = ""

            for char in answer:

                typed_text += char

                placeholder.markdown(
                    typed_text
                )

                time.sleep(0.002)

        except Exception as e:

            answer = (
                f"❌ Error: {str(e)}"
            )

            placeholder.error(
                answer
            )

    # ------------------------------------------
    # Save Assistant Response
    # ------------------------------------------

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
    
