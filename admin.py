import os
import json
import hashlib
import streamlit as st

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="KITTU AI — Admin",
    page_icon="🛡️",
    layout="wide"
)

# ==================================================
# PATHS  (always relative to project root)
# ==================================================

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
ADMIN_FILE = os.path.join(BASE_DIR, "admin_credentials.json")
DATA_DIR   = os.path.join(BASE_DIR, "user_data")
os.makedirs(DATA_DIR, exist_ok=True)

# ==================================================
# HELPERS
# ==================================================

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.strip().encode()).hexdigest()

def load_admin_creds() -> dict:
    if not os.path.exists(ADMIN_FILE):
        default = {"admin": hash_pw("admin123")}
        with open(ADMIN_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
        return default
    try:
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_admin_creds(creds: dict):
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)

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

def get_chat_count(username: str) -> int:
    path = os.path.join(DATA_DIR, username, "chat_history.json")
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0

def delete_user_data(username: str):
    import shutil
    user_dir = os.path.join(DATA_DIR, username)
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)

# ==================================================
# SESSION STATE
# ==================================================

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "admin_username" not in st.session_state:
    st.session_state.admin_username = ""

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
                st.session_state.admin_logged_in = True
                st.session_state.admin_username  = uname.strip()
                st.rerun()
            else:
                st.error("❌ Wrong username or password.")

        st.markdown("---")
        st.caption("Default: **admin** / **admin123**")

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
            elif len(p1) < 4:
                st.warning("Min 4 characters.")
            elif p1 != p2:
                st.error("Passwords don't match.")
            else:
                creds = load_admin_creds()
                creds[st.session_state.admin_username] = hash_pw(p1)
                save_admin_creds(creds)
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
    c1.metric("Total Users",       len(users))
    c2.metric("Total Saved Chats", sum(get_chat_count(u) for u in users))
    st.divider()

    # User table
    st.subheader("👥 All Users")
    if not users:
        st.info("No users registered yet.")
    else:
        hcols = st.columns([2, 3, 1, 2, 1])
        for h, c in zip(["Username", "Password Hash", "Chats", "Reset Password", "Delete"], hcols):
            c.markdown(f"**{h}**")
        st.markdown("---")

        for uname, pw_hash in list(users.items()):
            row = st.columns([2, 3, 1, 2, 1])
            row[0].markdown(f"👤 `{uname}`")
            row[1].markdown(f"`{pw_hash[:26]}…`")
            row[2].markdown(f"💬 {get_chat_count(uname)}")

            with row[3]:
                new_pw = st.text_input("pw", key=f"rpw_{uname}",
                                       placeholder="New password",
                                       label_visibility="collapsed")
                if st.button("🔄 Reset", key=f"rst_{uname}", use_container_width=True):
                    if not new_pw or len(new_pw) < 4:
                        st.warning("Min 4 chars.")
                    else:
                        users[uname] = hash_pw(new_pw)
                        save_users(users)
                        st.success(f"✅ Reset for {uname}")
                        st.rerun()

            with row[4]:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{uname}", use_container_width=True):
                    st.session_state[f"confirm_{uname}"] = True

            if st.session_state.get(f"confirm_{uname}"):
                with st.container(border=True):
                    st.warning(f"Delete **{uname}** and all their chats?")
                    y, n = st.columns(2)
                    if y.button("✅ Yes", key=f"y_{uname}", use_container_width=True, type="primary"):
                        del users[uname]
                        save_users(users)
                        delete_user_data(uname)
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
        nu = a1.text_input("Username", key="nu")
        np_ = a2.text_input("Password", type="password", key="np_")
        a3.markdown("<br>", unsafe_allow_html=True)
        if a3.button("Create", use_container_width=True, type="primary"):
            nu = nu.strip().lower()
            if not nu or not np_:
                st.error("Both fields required.")
            elif len(np_) < 4:
                st.error("Min 4 chars.")
            elif nu in users:
                st.error(f"'{nu}' already exists.")
            else:
                users[nu] = hash_pw(np_)
                save_users(users)
                st.success(f"✅ Created **{nu}**")
                st.rerun()

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
                import shutil
                if os.path.exists(USERS_FILE): os.remove(USERS_FILE)
                if os.path.exists(DATA_DIR):   shutil.rmtree(DATA_DIR)
                os.makedirs(DATA_DIR, exist_ok=True)
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
