import os
import time
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client, Client
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="KITTU AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

SESSION_COOKIE_NAME = "kittu_session_token"
SESSION_DURATION_DAYS = 30

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
# COOKIE MANAGER (this is what fixes the "logs out on
# every reload / mobile app switch" problem — Streamlit's
# session_state is wiped whenever the browser reconnects,
# so we store a long-lived session token in an actual
# browser cookie and re-validate it against Supabase on
# every load).
# ==================================================

def get_cookie_manager():
    # NOTE: intentionally NOT wrapped in @st.cache_resource.
    # CookieManager() renders an internal component (which Streamlit treats
    # as a "widget call"), and widget calls inside cached functions raise a
    # CachedWidgetWarning / behave unpredictably. The component manages its
    # own state across reruns on its own, so caching isn't needed here.
    return stx.CookieManager(key="kittu_cookie_manager")

cookie_manager = get_cookie_manager()


# ==================================================
# AUTH HELPERS
# ==================================================

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.strip().encode()).hexdigest()

def register_user(username: str, password: str) -> tuple[bool, str]:
    username = username.strip().lower()
    if not username or not password:
        return False, "Username and password cannot be empty."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    sb = get_supabase()
    res = sb.table("users").select("username").eq("username", username).execute()
    if res.data:
        return False, "Username already exists. Please choose another."
    sb.table("users").insert({"username": username, "password_hash": hash_pw(password)}).execute()
    return True, "Account created! You can now log in."

def verify_user(username: str, password: str) -> bool:
    username = username.strip().lower()
    if not username or not password:
        return False
    sb = get_supabase()
    res = sb.table("users").select("password_hash").eq("username", username).execute()
    if not res.data:
        return False
    return res.data[0]["password_hash"] == hash_pw(password)


# ==================================================
# PERSISTENT SESSION HELPERS (Supabase "sessions" table)
#
# Required Supabase table (run once in the SQL editor):
#
#   create table sessions (
#     token text primary key,
#     username text not null,
#     created_at timestamptz default now(),
#     expires_at timestamptz not null
#   );
#
# ==================================================

def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)).isoformat()
    sb = get_supabase()
    sb.table("sessions").insert({
        "token": token,
        "username": username,
        "expires_at": expires_at,
    }).execute()
    return token

def validate_session(token: str):
    if not token:
        return None
    try:
        sb = get_supabase()
        res = sb.table("sessions").select("username, expires_at").eq("token", token).execute()
        if not res.data:
            return None
        row = res.data[0]
        expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            delete_session(token)
            return None
        return row["username"]
    except Exception:
        # Sessions table missing/unreachable - treat as "not logged in"
        # rather than crashing the whole app.
        return None

def delete_session(token: str):
    if not token:
        return
    try:
        sb = get_supabase()
        sb.table("sessions").delete().eq("token", token).execute()
    except Exception:
        pass


def start_persistent_login(username: str):
    """Create a session row, then persist it two ways:
    1) A browser cookie (works well on desktop).
    2) A token embedded in the page URL itself (works everywhere, including
       mobile browsers/in-app webviews that block or wipe iframe-set cookies).
    If the user bookmarks or 'Adds to Home Screen' the URL *after* logging in
    (once it contains ?session=...), reopening that exact link logs them back
    in automatically, even after fully closing the app."""
    token = create_session(username)
    st.query_params["session"] = token
    try:
        expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)
        cookie_manager.set(
            SESSION_COOKIE_NAME,
            token,
            expires_at=expires_at,
            key="set_session_cookie",
        )
    except Exception:
        # Cookie failed (common on mobile/in-app browsers) - that's fine,
        # the URL token above still keeps them logged in.
        pass

def end_persistent_login():
    try:
        token = cookie_manager.get(SESSION_COOKIE_NAME)
        if token:
            delete_session(token)
        cookie_manager.delete(SESSION_COOKIE_NAME, key="delete_session_cookie")
    except Exception:
        pass
    qp_token = st.query_params.get("session")
    if qp_token:
        delete_session(qp_token)
    if "session" in st.query_params:
        del st.query_params["session"]


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
    ("chat_history", []),
    ("current_chat_id", None),
    ("confirm_clear_all", False),
    ("confirm_delete_chat", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ==================================================
# AUTO-LOGIN FROM COOKIE (runs on every fresh page load)
# ==================================================

if not st.session_state.logged_in:
    saved_token = st.query_params.get("session")
    if not saved_token:
        try:
            saved_token = cookie_manager.get(SESSION_COOKIE_NAME)
        except Exception:
            saved_token = None
    if saved_token:
        remembered_username = validate_session(saved_token)
        if remembered_username:
            st.session_state.logged_in = True
            st.session_state.username = remembered_username
            st.session_state.chat_history = load_user_history(remembered_username)
            st.session_state.messages = []
            st.session_state.current_chat_id = None
            # Make sure the URL keeps carrying the token so a bookmarked
            # link on mobile keeps working even if the cookie gets wiped.
            st.query_params["session"] = saved_token
            st.rerun()

# ==================================================
# CHAT HELPERS
# ==================================================

def _flush_current_chat():
    if not st.session_state.messages:
        return
    first_user_msg = next(
        (m["content"] for m in st.session_state.messages if m["role"] == "user"),
        "New Chat"
    )
    title = first_user_msg[:47] + "..." if len(first_user_msg) > 47 else first_user_msg
    new_id = save_chat_entry(
        st.session_state.username,
        title,
        st.session_state.messages,
        row_id=st.session_state.current_chat_id
    )
    st.session_state.current_chat_id = new_id
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
    st.markdown(
        "<h1 style='text-align:center;'>🤖 KITTU AI</h1>"
        "<p style='text-align:center;color:gray;'>Your personal AI assistant</p>",
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.container(border=True):
            mode = st.session_state.auth_mode
            st.markdown(f"#### {'🔐 Log in' if mode == 'login' else '📝 Create your account'}")

            username = st.text_input("Username", key="auth_username", placeholder="e.g. kittu_fan")
            password = st.text_input("Password", type="password", key="auth_password", placeholder="At least 4 characters")

            if mode == "login":
                remember = st.checkbox("Keep me logged in on this device", value=True)

                if st.button("Log in", use_container_width=True, type="primary"):
                    if not username or not password:
                        st.warning("⚠️ Please enter both a username and a password.")
                    else:
                        with st.spinner("Signing you in..."):
                            ok = verify_user(username, password)
                        if ok:
                            clean_username = username.strip().lower()
                            st.session_state.logged_in       = True
                            st.session_state.username        = clean_username
                            st.session_state.chat_history    = load_user_history(clean_username)
                            st.session_state.messages        = []
                            st.session_state.current_chat_id = None
                            if remember:
                                start_persistent_login(clean_username)
                            st.rerun()
                        else:
                            st.error("❌ Wrong username or password.")

                st.markdown("---")
                st.caption("Don't have an account yet?")
                if st.button("Create an account", use_container_width=True):
                    st.session_state.auth_mode = "register"
                    st.rerun()
            else:
                if st.button("Register", use_container_width=True, type="primary"):
                    if len(password) < 4:
                        st.error("❌ Password must be at least 4 characters.")
                    else:
                        with st.spinner("Creating your account..."):
                            ok, msg = register_user(username, password)
                        if ok:
                            st.success(f"✅ {msg}")
                            st.session_state.auth_mode = "login"
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

                st.markdown("---")
                st.caption("Already have an account?")
                if st.button("Back to login", use_container_width=True):
                    st.session_state.auth_mode = "login"
                    st.rerun()


# ==================================================
# MODEL
# ==================================================

MODEL_LABELS = {
    "⚡ Llama 3.1 8B — fast & lightweight": "meta-llama/Llama-3.1-8B-Instruct",
    "🧠 Qwen 2.5 72B — powerful & detailed": "Qwen/Qwen2.5-72B-Instruct",
    "🌀 Mistral 7B v0.3 — balanced": "mistralai/Mistral-7B-Instruct-v0.3",
    "🚀 DeepSeek V3 — cutting edge": "deepseek-ai/DeepSeek-V3-0324",
}

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
    st.markdown(
        f"<h2>🤖 KITTU AI &nbsp; <span style='font-size:0.6em;color:gray;'>👤 {st.session_state.username}</span></h2>",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.title("⚙️ Settings")

        with st.expander("🧩 Model options", expanded=False):
            model_label   = st.selectbox("Choose model", list(MODEL_LABELS.keys()))
            model_name    = MODEL_LABELS[model_label]
            temperature   = st.slider("Creativity (temperature)", 0.0, 2.0, 0.7, 0.1,
                                       help="Lower = more focused, higher = more creative/random")
            max_new_tokens = st.slider("Max response length", 128, 4096, 1024)

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            if st.button("➕ New chat", use_container_width=True):
                start_new_chat()
                st.rerun()
        with c2:
            if st.button("🗑️ Clear chat", use_container_width=True):
                if st.session_state.current_chat_id:
                    delete_chat_entry(st.session_state.current_chat_id)
                st.session_state.messages        = []
                st.session_state.current_chat_id = None
                st.session_state.chat_history    = load_user_history(st.session_state.username)
                st.rerun()

        if not st.session_state.confirm_clear_all:
            if st.button("🧹 Clear all history", use_container_width=True):
                st.session_state.confirm_clear_all = True
                st.rerun()
        else:
            st.warning("Delete **all** saved chats? This can't be undone.")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("✅ Yes, delete", use_container_width=True):
                    delete_all_history(st.session_state.username)
                    st.session_state.chat_history       = []
                    st.session_state.messages           = []
                    st.session_state.current_chat_id    = None
                    st.session_state.confirm_clear_all  = False
                    st.toast("History cleared!", icon="✅")
                    st.rerun()
            with cc2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.confirm_clear_all = False
                    st.rerun()

        st.divider()

        if st.button("🚪 Log out", use_container_width=True):
            _flush_current_chat()
            end_persistent_login()
            for k in ["logged_in", "username", "messages", "chat_history",
                      "current_chat_id", "confirm_clear_all", "confirm_delete_chat"]:
                del st.session_state[k]
            st.rerun()

        st.caption(
            "📌 On mobile: after logging in, use your browser's \"Add to Home Screen\" "
            "or bookmark option **now**, on this exact page. Reopening it from that "
            "shortcut will log you straight back in, even after fully closing the app."
        )

        st.divider()
        st.subheader("📜 Chat history")

        history = st.session_state.chat_history
        if not history:
            st.caption("No saved chats yet — start typing below!")
        else:
            for chat in reversed(history):
                is_active = (st.session_state.current_chat_id == chat["id"])
                row1, row2 = st.columns([5, 1])
                with row1:
                    label = f"▶ {chat['title']}" if is_active else f"💬 {chat['title']}"
                    if st.button(label, key=f"h_{chat['id']}", use_container_width=True):
                        _flush_current_chat()
                        st.session_state.messages        = chat["messages"]
                        st.session_state.current_chat_id = chat["id"]
                        st.rerun()
                with row2:
                    if st.button("🗑️", key=f"del_{chat['id']}"):
                        st.session_state.confirm_delete_chat = chat["id"]
                        st.rerun()

            if st.session_state.confirm_delete_chat is not None:
                st.warning("Delete this chat?")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("✅ Delete", key="confirm_del_yes", use_container_width=True):
                        delete_chat_entry(st.session_state.confirm_delete_chat)
                        if st.session_state.current_chat_id == st.session_state.confirm_delete_chat:
                            st.session_state.messages        = []
                            st.session_state.current_chat_id = None
                        st.session_state.chat_history = load_user_history(st.session_state.username)
                        st.session_state.confirm_delete_chat = None
                        st.rerun()
                with dc2:
                    if st.button("Cancel", key="confirm_del_no", use_container_width=True):
                        st.session_state.confirm_delete_chat = None
                        st.rerun()

    model = get_chat_model(model_name, temperature, max_new_tokens)

    if not st.session_state.messages:
        st.info("💡 Ask me anything to get started — try a question, a task, or paste some text to work on.")

    for msg in st.session_state.messages:
        avatar = "🧑" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask me anything...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)

        conversation = [SystemMessage(content="You are KITTU AI, a helpful and friendly assistant.")]
        for m in st.session_state.messages:
            if m["role"] == "user":
                conversation.append(HumanMessage(content=m["content"]))
            else:
                conversation.append(AIMessage(content=m["content"]))

        with st.chat_message("assistant", avatar="🤖"):
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
                answer = f"❌ Sorry, something went wrong: {str(e)}"
                placeholder.error(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})
        _flush_current_chat()


# ==================================================
# ROUTER
# ==================================================

if not st.session_state.logged_in:
    show_auth_screen()
else:
    show_main_app()import os
import hashlib
import streamlit as st
from supabase import create_client, Client

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="KITTU AI — Admin",
    page_icon="🛡️",
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
        st.error("❌ SUPABASE_URL and SUPABASE_KEY secrets are not set.")
        st.stop()
    return create_client(url, key)

# ==================================================
# HELPERS
# ==================================================

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.strip().encode()).hexdigest()

def load_admin_creds() -> dict:
    """Load admin credentials from Supabase.

    IMPORTANT: this never hardcodes a password in source code. The very
    first admin account is bootstrapped ONLY from the ADMIN_BOOTSTRAP_USERNAME
    / ADMIN_BOOTSTRAP_PASSWORD secrets (set these in your Streamlit/HF
    secrets, never commit them to the repo). Once that first login succeeds,
    change the password from the dashboard and you can remove those secrets.
    """
    sb = get_supabase()
    res = sb.table("admin_credentials").select("username, password_hash").execute()
    if res.data:
        return {row["username"]: row["password_hash"] for row in res.data}

    # No admin exists yet — bootstrap from secrets, not from hardcoded text.
    bootstrap_user = os.environ.get("ADMIN_BOOTSTRAP_USERNAME", "")
    bootstrap_pw   = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
    if not bootstrap_user or not bootstrap_pw:
        st.error(
            "❌ No admin account exists yet, and ADMIN_BOOTSTRAP_USERNAME / "
            "ADMIN_BOOTSTRAP_PASSWORD secrets are not set. Add them in your "
            "app's secrets, reload this page once to create the account, "
            "then remove those secrets and manage the password from the "
            "dashboard instead."
        )
        st.stop()

    sb.table("admin_credentials").insert({
        "username": bootstrap_user.strip(),
        "password_hash": hash_pw(bootstrap_pw)
    }).execute()
    return {bootstrap_user.strip(): hash_pw(bootstrap_pw)}

def update_admin_password(username: str, new_pw: str):
    sb = get_supabase()
    sb.table("admin_credentials") \
      .update({"password_hash": hash_pw(new_pw)}) \
      .eq("username", username) \
      .execute()

def load_users() -> list:
    sb = get_supabase()
    res = sb.table("users").select("username, password_hash").order("username").execute()
    return res.data if res.data else []

def get_chat_count(username: str) -> int:
    sb = get_supabase()
    res = sb.table("chat_history").select("id", count="exact").eq("username", username).execute()
    return res.count if res.count else 0

def reset_user_password(username: str, new_pw: str):
    sb = get_supabase()
    sb.table("users").update({"password_hash": hash_pw(new_pw)}).eq("username", username).execute()

def delete_user(username: str):
    sb = get_supabase()
    sb.table("chat_history").delete().eq("username", username).execute()
    sb.table("users").delete().eq("username", username).execute()

def create_user(username: str, password: str) -> tuple[bool, str]:
    sb = get_supabase()
    username = username.strip().lower()
    res = sb.table("users").select("username").eq("username", username).execute()
    if res.data:
        return False, f"'{username}' already exists."
    sb.table("users").insert({"username": username, "password_hash": hash_pw(password)}).execute()
    return True, f"User '{username}' created."

def wipe_everything():
    sb = get_supabase()
    sb.table("chat_history").delete().neq("id", 0).execute()
    sb.table("users").delete().neq("username", "").execute()

# ==================================================
# SESSION STATE
# ==================================================

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "admin_username" not in st.session_state:
    st.session_state.admin_username = ""
if "admin_login_attempts" not in st.session_state:
    st.session_state.admin_login_attempts = 0

# ==================================================
# LOGIN
# ==================================================

def show_login():
    st.title("🛡️ Admin Panel — KITTU AI")
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("### 🔐 Admin Login")
        uname = st.text_input("Username", key="al_user")
        pw    = st.text_input("Password", type="password", key="al_pass")

        if st.button("Login", use_container_width=True, type="primary"):
            creds = load_admin_creds()
            if uname.strip() in creds and creds[uname.strip()] == hash_pw(pw):
                st.session_state.admin_logged_in     = True
                st.session_state.admin_username      = uname.strip()
                st.session_state.admin_login_attempts = 0
                st.rerun()
            else:
                st.session_state.admin_login_attempts += 1
                st.error("❌ Wrong username or password.")
        # NOTE: no default credentials are ever shown here. The first admin
        # account is created from ADMIN_BOOTSTRAP_USERNAME/PASSWORD secrets —
        # see load_admin_creds() — never from on-screen text.

# ==================================================
# DASHBOARD
# ==================================================

def show_dashboard():
    st.title("🛡️ Admin Panel — KITTU AI")

    with st.sidebar:
        st.success(f"👤 **{st.session_state.admin_username}**")
        st.divider()
        st.subheader("🔑 Change Admin Password")
        p1 = st.text_input("New password",     type="password", key="ap1")
        p2 = st.text_input("Confirm password", type="password", key="ap2")
        if st.button("Update", use_container_width=True):
            if not p1:
                st.warning("Enter a password.")
            elif len(p1) < 8:
                st.warning("Use at least 8 characters.")
            elif p1 != p2:
                st.error("Passwords don't match.")
            else:
                update_admin_password(st.session_state.admin_username, p1)
                st.success("✅ Password updated!")
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.session_state.admin_username  = ""
            st.rerun()

    users = load_users()

    # Overview
    st.subheader("📊 Overview")
    c1, c2 = st.columns(2)
    c1.metric("Total Users", len(users))
    c2.metric("Total Saved Chats", sum(get_chat_count(u["username"]) for u in users))
    st.divider()

    # User table
    st.subheader("👥 All Users")
    if not users:
        st.info("No users registered yet.")
    else:
        hcols = st.columns([3, 1, 2, 1])
        for h, c in zip(["Username", "Chats", "Reset Password", "Delete"], hcols):
            c.markdown(f"**{h}**")
        st.markdown("---")

        for user in users:
            uname = user["username"]
            row   = st.columns([3, 1, 2, 1])

            row[0].markdown(f"👤 `{uname}`")
            row[1].markdown(f"💬 {get_chat_count(uname)}")

            with row[2]:
                new_pw = st.text_input("pw", key=f"rpw_{uname}",
                                       placeholder="New password",
                                       label_visibility="collapsed")
                if st.button("🔄 Reset", key=f"rst_{uname}", use_container_width=True):
                    if not new_pw or len(new_pw) < 4:
                        st.warning("Min 4 chars.")
                    else:
                        reset_user_password(uname, new_pw)
                        st.success(f"✅ Reset for {uname}")
                        st.rerun()

            with row[3]:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{uname}", use_container_width=True):
                    st.session_state[f"confirm_{uname}"] = True

            if st.session_state.get(f"confirm_{uname}"):
                with st.container(border=True):
                    st.warning(f"Delete **{uname}** and all their chats?")
                    y, n = st.columns(2)
                    if y.button("✅ Yes", key=f"y_{uname}", use_container_width=True, type="primary"):
                        delete_user(uname)
                        st.session_state.pop(f"confirm_{uname}", None)
                        st.success(f"Deleted {uname}.")
                        st.rerun()
                    if n.button("❌ No", key=f"n_{uname}", use_container_width=True):
                        st.session_state.pop(f"confirm_{uname}", None)
                        st.rerun()
            st.markdown("---")

    # Add user
    st.subheader("➕ Add New User")
    with st.container(border=True):
        a1, a2, a3 = st.columns([2, 2, 1])
        nu  = a1.text_input("Username", key="nu")
        np_ = a2.text_input("Password", type="password", key="np_")
        a3.markdown("<br>", unsafe_allow_html=True)
        if a3.button("Create", use_container_width=True, type="primary"):
            if not nu or not np_:
                st.error("Both fields required.")
            elif len(np_) < 4:
                st.error("Min 4 chars.")
            else:
                ok, msg = create_user(nu, np_)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

    st.divider()

    # Danger zone
    st.subheader("⚠️ Danger Zone")
    with st.container(border=True):
        st.warning("Permanently deletes **ALL users and ALL chat history**.")
        if st.button("🔥 Wipe Everything", type="primary"):
            st.session_state["nuke"] = True
        if st.session_state.get("nuke"):
            st.error("Cannot be undone. Sure?")
            y2, n2 = st.columns(2)
            if y2.button("Yes, delete all", use_container_width=True):
                wipe_everything()
                st.session_state["nuke"] = False
                st.success("Wiped.")
                st.rerun()
            if n2.button("Cancel", use_container_width=True):
                st.session_state["nuke"] = False
                st.rerun()

# ==================================================
# ROUTER
# ==================================================

if not st.session_state.admin_logged_in:
    show_login()
else:
    show_dashboard()
