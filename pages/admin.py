import os
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
    sb = get_supabase()
    res = sb.table("admin_credentials").select("username, password_hash").execute()
    if not res.data:
        # First time: insert default admin
        sb.table("admin_credentials").insert({
            "username": "kittuai",
            "password_hash": hash_pw("Payash@ADMIN26")
        }).execute()
        return {"kittuai": hash_pw("Payash@ADMIN26")}
    return {row["username"]: row["password_hash"] for row in res.data}

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
        st.caption("Default: **kittuai** / **Payash@ADMIN26**")

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
        hcols = st.columns([2, 3, 1, 2, 1])
        for h, c in zip(["Username", "Password Hash", "Chats", "Reset Password", "Delete"], hcols):
            c.markdown(f"**{h}**")
        st.markdown("---")

        for user in users:
            uname   = user["username"]
            pw_hash = user["password_hash"]
            row     = st.columns([2, 3, 1, 2, 1])

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
                        reset_user_password(uname, new_pw)
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
