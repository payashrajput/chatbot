import os
import time
import hashlib
import streamlit as st
from supabase import create_client, Client
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
# SUPABASE CLIENT
# ==================================================

@st.cache_resource
def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("❌ SUPABASE_URL and SUPABASE_KEY secrets are not set. Please add them in HuggingFace Space settings.")
        st.stop()
    return create_client(url, key)

# ==================================================
# AUTH HELPERS
# ==================================================

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.strip().encode()).hexdigest()

def register_user(username: str, password: str) -> tuple[bool, str]:
    username = username.strip().lower()
    if not username or not password:
        return False, "Username and password cannot be empty."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    sb = get_supabase()
    # Check if exists
    res = sb.table("users").select("username").eq("username", username).execute()
    if res.data:
        return False, "Username already exists. Please choose another."
    sb.table("users").insert({"username": username, "password_hash": hash_pw(password)}).execute()
    return True, "Account created! You can now log in."

def verify_user(username: str, password: str) -> bool:
    username = username.strip().lower()
    sb = get_supabase()
    res = sb.table("users").select("password_hash").eq("username", username).execute()
    if not res.data:
        return False
    return res.data[0]["password_hash"] == hash_pw(password)

# ==================================================
# CHAT HISTORY HELPERS
# ==================================================

def load_user_history(username: str) -> list:
    sb = get_supabase()
    res = sb.table("chat_history") \
            .select("id, title, messages") \
            .eq("username", username) \
            .order("created_at", desc=False) \
            .execute()
    return res.data if res.data else []

def save_chat_entry(username: str, title: str, messages: list, row_id=None):
    sb = get_supabase()
    if row_id:
        sb.table("chat_history") \
          .update({"title": title, "messages": messages}) \
          .eq("id", row_id) \
          .execute()
        return row_id
    else:
        res = sb.table("chat_history") \
                .insert({"username": username, "title": title, "messages": messages}) \
                .execute()
        return res.data[0]["id"] if res.data else None

def delete_all_history(username: str):
    sb = get_supabase()
    sb.table("chat_history").delete().eq("username", username).execute()

def delete_chat_entry(row_id):
    sb = get_supabase()
    sb.table("chat_history").delete().eq("id", row_id).execute()

# ==================================================
# SESSION STATE INIT
# ==================================================

for key, default in [
    ("logged_in", False),
    ("username", ""),
    ("auth_mode", "login"),
    ("messages", []),
    ("chat_history", []),       # list of {id, title, messages}
    ("current_chat_id", None),  # supabase row id
]:
    if key not in st.session_state:
        st.session_state[key] = default

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
    new_id = save_chat_entry(
        st.session_state.username,
        title,
        st.session_state.messages,
        row_id=st.session_state.current_chat_id
    )
    st.session_state.current_chat_id = new_id
    # Refresh local cache
    st.session_state.chat_history = load_user_history(st.session_state.username)

def start_new_chat():
    if st.session_state.messages:
        _flush_current_chat()
    st.session_state.messages        = []
    st.session_state.current_chat_id = None

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
                    st.session_state.logged_in       = True
                    st.session_state.username        = username.strip().lower()
                    st.session_state.chat_history    = load_user_history(st.session_state.username)
                    st.session_state.messages        = []
                    st.session_state.current_chat_id = None
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

def get_chat_model(repo_id, temp, tokens):
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

        model_name = st.selectbox("Choose Model", [
            "meta-llama/Llama-3.1-8B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "deepseek-ai/DeepSeek-V3-0324",
        ])
        temperature    = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
        max_new_tokens = st.slider("Max Tokens",  128, 4096, 1024)

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            if st.button("➕ New Chat", use_container_width=True):
                start_new_chat()
                st.rerun()
        with c2:
            if st.button("🗑️ Clear", use_container_width=True):
                if st.session_state.current_chat_id:
                    delete_chat_entry(st.session_state.current_chat_id)
                st.session_state.messages        = []
                st.session_state.current_chat_id = None
                st.session_state.chat_history    = load_user_history(st.session_state.username)
                st.rerun()

        if st.button("🧹 Clear All History", use_container_width=True):
            delete_all_history(st.session_state.username)
            st.session_state.chat_history    = []
            st.session_state.messages        = []
            st.session_state.current_chat_id = None
            st.success("History cleared!")
            st.rerun()

        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            _flush_current_chat()
            for k in ["logged_in", "username", "messages", "chat_history", "current_chat_id"]:
                del st.session_state[k]
            st.rerun()

        st.divider()
        st.subheader("📜 Chat History")

        history = st.session_state.chat_history
        if not history:
            st.caption("No history yet.")
        else:
            for chat in reversed(history):
                is_active = (st.session_state.current_chat_id == chat["id"])
                label     = f"▶ {chat['title']}" if is_active else f"💬 {chat['title']}"
                if st.button(label, key=f"h_{chat['id']}", use_container_width=True):
                    _flush_current_chat()
                    st.session_state.messages        = chat["messages"]
                    st.session_state.current_chat_id = chat["id"]
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
