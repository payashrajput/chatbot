import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

import os
import json
import time

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(page_title="KITTU AI", page_icon="🤖", layout="wide")

# ==================================================
# LOAD CONFIG
# ==================================================

with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"]
)

authenticator.login()

# ==================================================
# LOGIN CHECK
# ==================================================

if st.session_state.get("authentication_status") is False:
    st.error("❌ Wrong username/password")

if st.session_state.get("authentication_status") is None:
    st.warning("🔐 Please login")
    st.stop()

if st.session_state.get("authentication_status"):

    authenticator.logout("Logout", "sidebar")

    st.sidebar.success(f"Welcome {st.session_state['name']}")

# ==================================================
# CHAT APP
# ==================================================

HISTORY_FILE = "chat_history.json"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            st.session_state.chat_history = json.load(f)
    else:
        st.session_state.chat_history = []

def save_history():
    with open(HISTORY_FILE, "w") as f:
        json.dump(st.session_state.chat_history, f, indent=2)

# ==================================================
# MODEL
# ==================================================

@st.cache_resource
def load_model():
    return ChatHuggingFace(
        llm=HuggingFaceEndpoint(
            repo_id="mistralai/Mistral-7B-Instruct-v0.3",
            task="text-generation",
            temperature=0.7,
            max_new_tokens=1024
        )
    )

model = load_model()

# ==================================================
# UI
# ==================================================

st.title("🤖 KITTU AI")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Ask me anything...")

if prompt:

    st.session_state.messages.append({"role": "user", "content": prompt})

    conversation = [
        SystemMessage(content="You are KITTU AI assistant.")
    ]

    for m in st.session_state.messages:
        if m["role"] == "user":
            conversation.append(HumanMessage(content=m["content"]))
        else:
            conversation.append(AIMessage(content=m["content"]))

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("Thinking...")

        try:
            response = model.invoke(conversation)
            answer = response.content

            text = ""
            for c in answer:
                text += c
                placeholder.markdown(text)
                time.sleep(0.002)

        except Exception as e:
            answer = str(e)
            placeholder.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})import os
import json
import time
import streamlit as st

from authlib.integrations.requests_client import OAuth2Session

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

# ==================================================
# GOOGLE OAUTH CONFIG
# ==================================================

CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

scope = "openid email profile"

oauth = OAuth2Session(
    CLIENT_ID,
    CLIENT_SECRET,
    scope=scope,
    redirect_uri=REDIRECT_URI
)

# ==================================================
# LOGIN SYSTEM
# ==================================================

if "user" not in st.session_state:

    st.title("🤖 KITTU AI Login")

    auth_url, state = oauth.create_authorization_url(AUTHORIZE_URL)

    st.markdown(f"### 👉 [Login with Google]({auth_url})")

    code = st.query_params.get("code")

    if code:

        try:
            token = oauth.fetch_token(
                TOKEN_URL,
                code=code
            )

            st.session_state["token"] = token

            user_info = oauth.get(USERINFO_URL).json()

            st.session_state["user"] = user_info

            st.rerun()

        except Exception as e:
            st.error(f"Login failed: {e}")

    st.stop()

# ==================================================
# USER INFO
# ==================================================

user = st.session_state["user"]

st.sidebar.image(user["picture"])
st.sidebar.write(f"👤 {user['name']}")
st.sidebar.write(f"📧 {user['email']}")

if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

# ==================================================
# HISTORY
# ==================================================

HISTORY_FILE = "chat_history.json"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:

    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                st.session_state.chat_history = json.load(f)
        except:
            st.session_state.chat_history = []
    else:
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

    st.subheader("📜 Chat History")

    for i, chat in enumerate(reversed(st.session_state.chat_history)):
        if st.button(chat["title"], key=i):
            st.session_state.messages = chat["messages"]
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
# CHAT UI
# ==================================================

st.title("🤖 KITTU AI")

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

    with st.chat_message("user"):
        st.markdown(prompt)

    conversation = [
        SystemMessage(content="You are KITTU AI, a helpful assistant.")
    ]

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            conversation.append(HumanMessage(content=msg["content"]))
        else:
            conversation.append(AIMessage(content=msg["content"]))

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
            answer = f"Error: {e}"
            placeholder.error(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
