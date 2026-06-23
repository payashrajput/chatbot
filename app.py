import os
import time
import base64
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
# IMAGE HELPERS
# ==================================================

def image_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")

def build_vision_message(prompt: str, image_b64: str, mime_type: str = "image/jpeg") -> HumanMessage:
    """Build a HumanMessage with both text and image for vision models."""
    return HumanMessage(content=[
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{image_b64}"
            }
        },
        {
            "type": "text",
            "text": prompt
        }
    ])

def get_image_mime_type(file_name: str) -> str:
    """Determine MIME type from file extension."""
    ext = file_name.lower().split(".")[-1]
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(ext, "image/jpeg")

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
    ("input_mode", "text"),       # "text", "upload", or "camera"
    ("pending_image_b64", None),  # base64 of staged image
    ("pending_image_mime", None), # mime type of staged image
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
        (m["content"][:50] if isinstance(m["content"], str) else "Image Chat"
         for m in st.session_state.messages if m["role"] == "user"),
        "New Chat"
    )
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
    st.session_state.pending_image_b64  = None
    st.session_state.pending_image_mime = None

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
# RENDER CHAT MESSAGE (handles text + image history)
# ==================================================

def render_message(msg: dict):
    """Render a stored message, which may contain image data."""
    with st.chat_message(msg["role"]):
        content = msg["content"]
        if isinstance(content, list):
            # Multi-part message (image + text)
            for part in content:
                if part.get("type") == "text":
                    st.markdown(part["text"])
                elif part.get("type") == "image_url":
                    url = part["image_url"]["url"]
                    # Display inline base64 image
                    st.image(url, width=300)
        else:
            st.markdown(content)

# ==================================================
# MAIN APP
# ==================================================

def show_main_app():
    st.title(f"🤖 KITTU AI  —  👤 {st.session_state.username}")

    with st.sidebar:
        st.title("⚙️ Settings")

        # Text models
        TEXT_MODELS = [
            "meta-llama/Llama-3.1-8B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "deepseek-ai/DeepSeek-V3-0324",
        ]
        # Vision models (support image input)
        VISION_MODELS = [
            "llava-hf/llava-1.5-7b-hf",
            "Qwen/Qwen2-VL-7B-Instruct",
            "microsoft/Phi-3.5-vision-instruct",
        ]

        has_image = st.session_state.pending_image_b64 is not None

        if has_image:
            st.info("🖼️ Vision mode active — using a vision model.")
            model_name = st.selectbox("Vision Model", VISION_MODELS)
        else:
            model_name = st.selectbox("Choose Model", TEXT_MODELS)

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
                st.session_state.pending_image_b64  = None
                st.session_state.pending_image_mime = None
                st.session_state.chat_history    = load_user_history(st.session_state.username)
                st.rerun()

        if st.button("🧹 Clear All History", use_container_width=True):
            delete_all_history(st.session_state.username)
            st.session_state.chat_history    = []
            st.session_state.messages        = []
            st.session_state.current_chat_id = None
            st.session_state.pending_image_b64  = None
            st.session_state.pending_image_mime = None
            st.success("History cleared!")
            st.rerun()

        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            _flush_current_chat()
            for k in ["logged_in", "username", "messages", "chat_history", "current_chat_id",
                      "pending_image_b64", "pending_image_mime"]:
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

    # --------------------------------------------------
    # CHAT MESSAGES
    # --------------------------------------------------
    for msg in st.session_state.messages:
        render_message(msg)

    # --------------------------------------------------
    # IMAGE INPUT CONTROLS  (above chat input)
    # --------------------------------------------------
    st.markdown("#### 📎 Attach an Image (optional)")

    mode_col1, mode_col2, mode_col3 = st.columns([1, 1, 4])
    with mode_col1:
        upload_active = st.session_state.input_mode == "upload"
        if st.button(
            "✅ Upload Photo" if upload_active else "📁 Upload Photo",
            use_container_width=True,
            type="primary" if upload_active else "secondary",
        ):
            if st.session_state.input_mode == "upload":
                # Close uploader — but only clear image if user explicitly removes it
                st.session_state.input_mode = "text"
            else:
                st.session_state.input_mode = "upload"
            st.rerun()

    with mode_col2:
        cam_active = st.session_state.input_mode == "camera"
        if st.button(
            "✅ Camera" if cam_active else "📷 Camera",
            use_container_width=True,
            type="primary" if cam_active else "secondary",
        ):
            if st.session_state.input_mode == "camera":
                st.session_state.input_mode = "text"
            else:
                st.session_state.input_mode = "camera"
            st.rerun()

    # --------------------------------------------------
    # CAMERA PERMISSION POPUP via JS (runs once when camera mode opens)
    # --------------------------------------------------
    if st.session_state.input_mode == "camera":
        # Inject a tiny JS snippet that calls getUserMedia so the browser
        # shows its native "Allow camera access?" permission dialog.
        # This fires before st.camera_input renders, giving the user a
        # proper permission prompt instead of a silent failure.
        st.components.v1.html(
            """
            <script>
            (function() {
                // Only request if not already granted
                if (!window._kittuCamRequested) {
                    window._kittuCamRequested = true;
                    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                        navigator.mediaDevices.getUserMedia({ video: true })
                            .then(function(stream) {
                                // Stop tracks immediately — we just needed the permission grant.
                                // Streamlit's camera_input will open its own stream.
                                stream.getTracks().forEach(function(t) { t.stop(); });
                            })
                            .catch(function(err) {
                                // Permission denied — show a friendly message in the parent page
                                var msg = document.createElement('div');
                                msg.style.cssText =
                                    'position:fixed;top:16px;left:50%;transform:translateX(-50%);' +
                                    'background:#ff4b4b;color:#fff;padding:12px 24px;border-radius:8px;' +
                                    'font-family:sans-serif;font-size:14px;z-index:99999;box-shadow:0 4px 12px rgba(0,0,0,.3);';
                                msg.textContent =
                                    '❌ Camera access denied. Please allow camera in your browser settings and try again.';
                                document.body.appendChild(msg);
                                setTimeout(function() { msg.remove(); }, 5000);
                            });
                    }
                }
            })();
            </script>
            """,
            height=0,
        )

    # --------------------------------------------------
    # Show uploader or camera widget based on mode
    # --------------------------------------------------
    if st.session_state.input_mode == "upload":
        uploaded_file = st.file_uploader(
            "📂 Choose a photo (JPG, PNG, WEBP, GIF)",
            type=["jpg", "jpeg", "png", "webp", "gif"],
        )
        if uploaded_file is not None:
            mime = get_image_mime_type(uploaded_file.name)
            b64  = image_to_base64(uploaded_file.read())
            st.session_state.pending_image_b64  = b64
            st.session_state.pending_image_mime = mime
            # Show preview
            st.image(f"data:{mime};base64,{b64}", caption="📎 Image ready to send", width=300)
        elif st.session_state.pending_image_b64 and st.session_state.pending_image_mime:
            # Uploader cleared by user — respect that
            pass

    elif st.session_state.input_mode == "camera":
        st.info("📷 Point your camera and click **Take photo**. Make sure to **Allow** camera access when prompted by your browser.", icon="ℹ️")
        camera_photo = st.camera_input("Take a photo", label_visibility="collapsed")
        if camera_photo is not None:
            b64 = image_to_base64(camera_photo.read())
            st.session_state.pending_image_b64  = b64
            st.session_state.pending_image_mime = "image/jpeg"
            st.image(
                f"data:image/jpeg;base64,{b64}",
                caption="📷 Photo captured — ready to send",
                width=300,
            )

    # Show staged image badge when panel is closed
    if st.session_state.pending_image_b64 and st.session_state.input_mode == "text":
        st.success("🖼️ Image attached and ready to send with your next message.")

    # Clear staged image button
    if st.session_state.pending_image_b64:
        if st.button("❌ Remove attached image", key="clear_img"):
            st.session_state.pending_image_b64  = None
            st.session_state.pending_image_mime = None
            st.session_state.input_mode         = "text"
            st.rerun()

    st.markdown("---")

    # --------------------------------------------------
    # CHAT INPUT
    # --------------------------------------------------
    prompt = st.chat_input("Ask me anything… or describe the image above ⬆️")

    if prompt:
        model = get_chat_model(model_name, temperature, max_new_tokens)

        image_b64  = st.session_state.pending_image_b64
        image_mime = st.session_state.pending_image_mime or "image/jpeg"

        # Build stored message content
        if image_b64:
            user_content = [
                {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ]
        else:
            user_content = prompt

        st.session_state.messages.append({"role": "user", "content": user_content})

        # Display user message immediately
        render_message({"role": "user", "content": user_content})

        # Build conversation for the model
        conversation = [SystemMessage(content="You are KITTU AI, a helpful and friendly assistant. When given an image, describe and analyze it thoroughly before answering any questions about it.")]

        for m in st.session_state.messages[:-1]:  # history (excluding current)
            if m["role"] == "user":
                if isinstance(m["content"], list):
                    conversation.append(HumanMessage(content=m["content"]))
                else:
                    conversation.append(HumanMessage(content=m["content"]))
            else:
                content = m["content"]
                if isinstance(content, list):
                    text_parts = " ".join(p["text"] for p in content if p.get("type") == "text")
                    conversation.append(AIMessage(content=text_parts))
                else:
                    conversation.append(AIMessage(content=content))

        # Add current message
        if image_b64:
            conversation.append(build_vision_message(prompt, image_b64, image_mime))
        else:
            conversation.append(HumanMessage(content=prompt))

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

        # Clear staged image after sending
        st.session_state.pending_image_b64  = None
        st.session_state.pending_image_mime = None
        st.session_state.input_mode         = "text"

        _flush_current_chat()

# ==================================================
# ROUTER
# ==================================================

if not st.session_state.logged_in:
    show_auth_screen()
else:
    show_main_app()
