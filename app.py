import os
import json
import time
import hashlib
import streamlit as st

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="KITTU AI",
    page_icon="🤖",
    layout="wide"
)

# ==================================================
# PATHS
# ==================================================

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
DATA_DIR   = os.path.join(BASE_DIR, "user_data")
os.makedirs(DATA_DIR, exist_ok=True)

# ==================================================
# AUTH HELPERS
# ==================================================

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.strip().encode()).hexdigest()

def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(users: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def register_user(username: str, password: str) -> tuple[bool, str]:
    users = load_users()
    username = username.strip().lower()
    if not username or not password:
        return False, "Username and password cannot be empty."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    if username in users:
        return False, "Username already exists. Please choose another."
    users[username] = hash_pw(password)
    save_users(users)
    return True, "Account created! You can now log in."

def verify_user(username: str, password: str) -> bool:
    users = load_users()
    return users.get(username.strip().lower()) == hash_pw(password)

# ==================================================
# PER-USER HISTORY HELPERS
# ==================================================

def history_file(username: str) -> str:
    user_dir = os.path.join(DATA_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, "chat_history.json")

def load_user_history(username: str) -> list:
    path = history_file(username)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_user_history(username: str, history: list):
    with open(history_file(username), "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# ==================================================
# SESSION STATE INIT
# ==================================================

for key, default in [
    ("logged_in", False),
    ("username", ""),
    ("auth_mode", "login"),
    ("messages", []),
    ("chat_history", []),
    ("current_chat_index", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ==================================================
# LOGIN / REGISTER SCREEN
# ==================================================

def show_auth_screen():
    st.title("🤖 KITTU AI")
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        mode = st.session_state.auth_mode
        st.markdown(f"### {'🔐 Login' if mode == 'login' else '📝 Create Account'}")

        username = st.text_input("Username", key="auth_username")
        password = st.text_input("Password", type="password", key="auth_password")

        if mode == "login":
            if st.button("Login", use_container_width=True, type="primary"):
                if verify_user(username, password):
                    st.session_state.logged_in    = True
                    st.session_state.username     = username.strip().lower()
                    st.session_state.chat_history = load_user_history(st.session_state.username)
                    st.session_state.messages     = []
                    st.session_state.current_chat_index = None
                    st.rerun()
                else:
                    st.error("❌ Wrong username or password.")
            st.markdown("---")
            st.caption("Don't have an account?")
            if st.button("Create Account", use_container_width=True):
                st.session_state.auth_mode = "register"
                st.rerun()

        else:
            if st.button("Register", use_container_width=True, type="primary"):
                ok, msg = register_user(username, password)
                if ok:
                    st.success(f"✅ {msg}")
                    st.session_state.auth_mode = "login"
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            st.markdown("---")
            st.caption("Already have an account?")
            if st.button("Back to Login", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()

# ==================================================
# CHAT HELPERS
# ==================================================

def _flush_current_chat():
    if not st.session_state.messages:
        return
    title = next(
        (m["content"][:50] for m in st.session_state.messages if m["role"] == "user"),
        "New Chat"
    )
    entry = {"title": title, "messages": st.session_state.messages.copy()}
    idx = st.session_state.current_chat_index
    if idx is not None and 0 <= idx < len(st.session_state.chat_history):
        st.session_state.chat_history[idx] = entry
    else:
        st.session_state.chat_history.append(entry)
        st.session_state.current_chat_index = len(st.session_state.chat_history) - 1
    save_user_history(st.session_state.username, st.session_state.chat_history)

def start_new_chat():
    if st.session_state.messages:
        _flush_current_chat()
    st.session_state.messages = []
    st.session_state.current_chat_index = None

# ==================================================
# MODEL
# ==================================================

@st.cache_resource(show_spinner=False)
def load_llm(repo_id: str):
    return HuggingFaceEndpoint(
        repo_id=repo_id,
        task="text-generation",
        temperature=0.7,
        max_new_tokens=1024,
    )

def get_chat_model(repo_id: str, temp: float, tokens: int):
    llm = load_llm(repo_id)
    llm.temperature    = temp
    llm.max_new_tokens = tokens
    return ChatHuggingFace(llm=llm)

# ==================================================
# MAIN APP
# ==================================================

def show_main_app():
    st.title(f"🤖 KITTU AI  —  👤 {st.session_state.username}")

    with st.sidebar:
        st.title("⚙️ Settings")

        model_name = st.selectbox(
            "Choose Model",
            [
                "meta-llama/Llama-3.1-8B-Instruct",
                "Qwen/Qwen2.5-72B-Instruct",
                "mistralai/Mistral-7B-Instruct-v0.3",
                "deepseek-ai/DeepSeek-V3-0324",
            ]
        )
        temperature    = st.slider("Temperature",  0.0, 2.0, 0.7, 0.1)
        max_new_tokens = st.slider("Max Tokens",   128, 4096, 1024)

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            if st.button("➕ New Chat", use_container_width=True):
                start_new_chat()
                st.rerun()
        with c2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.messages = []
                st.session_state.current_chat_index = None
                st.rerun()

        if st.button("🧹 Clear All History", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.messages     = []
            st.session_state.current_chat_index = None
            save_user_history(st.session_state.username, [])
            st.success("History cleared!")
            st.rerun()

        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            _flush_current_chat()
            for key in ["logged_in", "username", "messages",
                        "chat_history", "current_chat_index"]:
                del st.session_state[key]
            st.rerun()

        st.divider()
        st.subheader("📜 Chat History")

        if not st.session_state.chat_history:
            st.caption("No history yet.")
        else:
            for i, chat in enumerate(reversed(st.session_state.chat_history)):
                real_index = len(st.session_state.chat_history) - 1 - i
                is_active  = (st.session_state.current_chat_index == real_index)
                label      = f"▶ {chat.get('title','New Chat')}" if is_active else f"💬 {chat.get('title','New Chat')}"
                if st.button(label, key=f"history_{real_index}", use_container_width=True):
                    _flush_current_chat()
                    st.session_state.messages = chat.get("messages", []).copy()
                    st.session_state.current_chat_index = real_index
                    st.rerun()

    model = get_chat_model(model_name, temperature, max_new_tokens)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask me anything...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        conversation = [SystemMessage(content="You are KITTU AI, a helpful and friendly assistant.")]
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
                answer   = response.content.strip()
                streamed = ""
                for char in answer:
                    streamed += char
                    placeholder.markdown(streamed + "▌")
                    time.sleep(0.008)
                placeholder.markdown(streamed)
            except Exception as e:
                answer = f"❌ Error: {str(e)}"
                placeholder.error(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})
        _flush_current_chat()

# ==================================================
# ROUTER
# ==================================================

if not st.session_state.logged_in:
    show_auth_screen()
else:
    show_main_app()
