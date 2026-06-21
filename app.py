import os
import json
import time
import streamlit as st

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

st.title("🤖AI CHATBOT")

HISTORY_FILE = "chat_history.json"

# ==================================================
# SESSION STATE INIT (only once)
# ==================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    # Load from file only on first run
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.chat_history = data if isinstance(data, list) else []
        except Exception:
            st.session_state.chat_history = []
    else:
        st.session_state.chat_history = []

if "current_chat_index" not in st.session_state:
    st.session_state.current_chat_index = None  # Tracks which saved chat is active

# ==================================================
# HISTORY HELPERS
# ==================================================

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.chat_history, f, indent=2, ensure_ascii=False)


def start_new_chat():
    """Save current chat (if non-empty) then reset."""
    if st.session_state.messages:
        _flush_current_chat()
    st.session_state.messages = []
    st.session_state.current_chat_index = None


def _flush_current_chat():
    """Update or insert the current session into chat_history."""
    if not st.session_state.messages:
        return

    title = next(
        (m["content"][:50] for m in st.session_state.messages if m["role"] == "user"),
        "New Chat"
    )
    entry = {"title": title, "messages": st.session_state.messages.copy()}

    idx = st.session_state.current_chat_index
    if idx is not None and 0 <= idx < len(st.session_state.chat_history):
        st.session_state.chat_history[idx] = entry  # Update in place
    else:
        st.session_state.chat_history.append(entry)
        st.session_state.current_chat_index = len(st.session_state.chat_history) - 1

    save_history()

# ==================================================
# SIDEBAR
# ==================================================

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

    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
    max_new_tokens = st.slider("Max Tokens", 128, 4096, 1024)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("➕ New Chat", use_container_width=True):
            start_new_chat()
            st.rerun()

    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_chat_index = None
            st.rerun()

    if st.button("🧹 Clear All History", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.messages = []
        st.session_state.current_chat_index = None
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.success("All history cleared!")
        st.rerun()

    st.divider()
    st.subheader("📜 Chat History")

    if not st.session_state.chat_history:
        st.caption("No history yet.")
    else:
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            real_index = len(st.session_state.chat_history) - 1 - i
            title = chat.get("title", "New Chat")
            is_active = st.session_state.current_chat_index == real_index

            label = f"▶ {title}" if is_active else f"💬 {title}"
            if st.button(label, key=f"history_{real_index}", use_container_width=True):
                _flush_current_chat()  # Save current before switching
                st.session_state.messages = chat.get("messages", []).copy()
                st.session_state.current_chat_index = real_index
                st.rerun()

# ==================================================
# MODEL — cache only on repo_id; re-init if settings change
# ==================================================

@st.cache_resource(show_spinner=False)
def load_llm(repo_id: str):
    """Cache the endpoint per model. Temperature/tokens are passed at invoke time."""
    return HuggingFaceEndpoint(
        repo_id=repo_id,
        task="text-generation",
        temperature=0.7,       # default; overridden below at invoke
        max_new_tokens=1024,
    )


def get_chat_model(repo_id: str, temp: float, tokens: int):
    """Wrap cached LLM, overriding generation params each time."""
    llm = load_llm(repo_id)
    llm.temperature = temp
    llm.max_new_tokens = tokens
    return ChatHuggingFace(llm=llm)


model = get_chat_model(model_name, temperature, max_new_tokens)

# ==================================================
# DISPLAY CHAT HISTORY
# ==================================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==================================================
# CHAT INPUT
# ==================================================

prompt = st.chat_input("Ask me anything...")

if prompt:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build conversation for LLM
    conversation = [SystemMessage(content="You are KITTU AI, a helpful and friendly assistant.")]
    for m in st.session_state.messages:
        if m["role"] == "user":
            conversation.append(HumanMessage(content=m["content"]))
        else:
            conversation.append(AIMessage(content=m["content"]))

    # Get response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ Thinking...")

        try:
            response = model.invoke(conversation)
            answer = response.content.strip()

            # Simulate streaming (character-by-character)
            streamed = ""
            for char in answer:
                streamed += char
                placeholder.markdown(streamed + "▌")
                time.sleep(0.008)
            placeholder.markdown(streamed)

        except Exception as e:
            answer = f"❌ Error: {str(e)}"
            placeholder.error(answer)

    # Append assistant message
    st.session_state.messages.append({"role": "assistant", "content": answer})

    # Persist to history (update existing or create new entry)
    _flush_current_chat()
