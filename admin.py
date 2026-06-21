import os
import json
import hashlib
import streamlit as st

# ==================================================
# CONFIG
# ==================================================

st.set_page_config(
    page_title="KITTU AI — Admin Panel",
    page_icon="🛡️",
    layout="wide"
)

USERS_FILE   = "users.json"
DATA_DIR     = "user_data"
ADMIN_CREDS  = {"kittuai": hashlib.sha256("Payash@ADMIN26".encode()).hexdigest()}
# ⚠️  Change the password above before deploying!

# ==================================================
# HELPERS
# ==================================================

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

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

def get_user_history_count(username: str) -> int:
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

# ==================================================
# ADMIN LOGIN
# ==================================================

def show_admin_login():
    st.title("🛡️ Admin Panel — KITTU AI")

    col_l, col_c, col_r = st.columns([1, 1, 1])
    with col_c:
        st.markdown("### 🔐 Admin Login")
        username = st.text_input("Admin Username", key="admin_user")
        password = st.text_input("Admin Password", type="password", key="admin_pass")

        if st.button("Login as Admin", use_container_width=True, type="primary"):
            if ADMIN_CREDS.get(username) == hash_pw(password):
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("❌ Invalid admin credentials.")

        st.caption("⚠️ This panel is for administrators only.")

# ==================================================
# ADMIN DASHBOARD
# ==================================================

def show_admin_panel():
    st.title("🛡️ Admin Panel — KITTU AI")

    if st.sidebar.button("🚪 Logout Admin"):
        st.session_state.admin_logged_in = False
        st.rerun()

    st.sidebar.success("Logged in as **admin**")
    st.sidebar.caption("Manage all users and their data from here.")

    users = load_users()

    # ── Stats row ──────────────────────────────────
    st.subheader("📊 Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Users", len(users))
    total_chats = sum(get_user_history_count(u) for u in users)
    c2.metric("Total Saved Chats", total_chats)
    c3.metric("Data Folder", DATA_DIR)

    st.divider()

    # ── User Table ─────────────────────────────────
    st.subheader("👥 All Users")

    if not users:
        st.info("No users registered yet.")
    else:
        col_h = st.columns([2, 2, 1, 2, 2])
        for header, col in zip(["Username", "Password Hash", "Saved Chats", "Reset Password", "Actions"], col_h):
            col.markdown(f"**{header}**")
        st.markdown("---")

        for username, pw_hash in list(users.items()):
            cols = st.columns([2, 2, 1, 2, 2])

            cols[0].markdown(f"👤 `{username}`")
            cols[1].markdown(f"`{pw_hash[:20]}...`")
            cols[2].markdown(f"💬 {get_user_history_count(username)}")

            with cols[3]:
                new_pw = st.text_input(
                    "New password",
                    key=f"reset_pw_{username}",
                    placeholder="New password",
                    label_visibility="collapsed"
                )
                if st.button("🔄 Reset", key=f"btn_reset_{username}", use_container_width=True):
                    if not new_pw:
                        st.warning("Enter a new password first.")
                    elif len(new_pw) < 4:
                        st.warning("Password too short (min 4 chars).")
                    else:
                        users[username] = hash_pw(new_pw)
                        save_users(users)
                        st.success(f"✅ Password reset for **{username}**")
                        st.rerun()

            with cols[4]:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"btn_del_{username}", use_container_width=True):
                    st.session_state[f"confirm_delete_{username}"] = True

            if st.session_state.get(f"confirm_delete_{username}"):
                with st.container(border=True):
                    st.warning(
                        f"⚠️ Delete **{username}**? This removes their account AND all chat history."
                    )
                    yes_col, no_col = st.columns(2)
                    if yes_col.button("✅ Yes, Delete", key=f"yes_{username}",
                                      use_container_width=True, type="primary"):
                        del users[username]
                        save_users(users)
                        delete_user_data(username)
                        del st.session_state[f"confirm_delete_{username}"]
                        st.success(f"Deleted **{username}**.")
                        st.rerun()
                    if no_col.button("❌ Cancel", key=f"no_{username}",
                                     use_container_width=True):
                        del st.session_state[f"confirm_delete_{username}"]
                        st.rerun()

            st.markdown("---")

    st.divider()

    # ── Add New User ───────────────────────────────
    st.subheader("➕ Add New User")
    with st.container(border=True):
        a1, a2, a3 = st.columns([2, 2, 1])
        new_user = a1.text_input("Username", key="new_user_input")
        new_pass = a2.text_input("Password", type="password", key="new_pass_input")
        a3.markdown("<br>", unsafe_allow_html=True)
        if a3.button("Create User", use_container_width=True, type="primary"):
            new_user_clean = new_user.strip().lower()
            if not new_user_clean or not new_pass:
                st.error("Both fields are required.")
            elif len(new_pass) < 4:
                st.error("Password must be at least 4 characters.")
            elif new_user_clean in users:
                st.error(f"User '{new_user_clean}' already exists.")
            else:
                users[new_user_clean] = hash_pw(new_pass)
                save_users(users)
                st.success(f"✅ User **{new_user_clean}** created!")
                st.rerun()

    st.divider()

    # ── Danger Zone ────────────────────────────────
    st.subheader("⚠️ Danger Zone")
    with st.container(border=True):
        st.warning("This will permanently delete **ALL users and ALL chat history**.")
        if st.button("🔥 Delete Everything", type="primary"):
            st.session_state["confirm_nuke"] = True

        if st.session_state.get("confirm_nuke"):
            st.error("Are you absolutely sure? This cannot be undone.")
            y, n = st.columns(2)
            if y.button("Yes, wipe everything", use_container_width=True):
                import shutil
                if os.path.exists(USERS_FILE):
                    os.remove(USERS_FILE)
                if os.path.exists(DATA_DIR):
                    shutil.rmtree(DATA_DIR)
                os.makedirs(DATA_DIR, exist_ok=True)
                st.session_state["confirm_nuke"] = False
                st.success("Everything wiped.")
                st.rerun()
            if n.button("Cancel", use_container_width=True):
                st.session_state["confirm_nuke"] = False
                st.rerun()

# ==================================================
# ROUTER
# ==================================================

if not st.session_state.admin_logged_in:
    show_admin_login()
else:
    show_admin_panel()
