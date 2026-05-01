from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
import anthropic
import PyPDF2
import io

# ============================================
# Config
# ============================================
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

st.set_page_config(
    page_title="SmartDocs",
    page_icon="📄",
    layout="centered",
)

# ============================================
# Custom CSS
# ============================================
st.markdown("""
<style>
    .main { max-width: 760px; }
    .stAlert { border-radius: 8px; }
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
    }
    .doc-badge {
        background: #f0f2f6;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 0.875rem;
        color: #374151;
        display: inline-block;
        margin-bottom: 8px;
    }
    .api-section {
        background: #fafafa;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# Session state init
# ============================================
defaults = {
    "document_text": None,
    "document_name": None,
    "chat_history": [],
    "api_key": "",
    "client": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ============================================
# Helpers
# ============================================
def get_client():
    """Return an Anthropic client, preferring user-supplied key."""
    key = st.session_state["api_key"].strip()
    if not key:
        # Fall back to environment / Streamlit secrets
        try:
            key = st.secrets["ANTHROPIC_API_KEY"]
        except Exception:
            key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)


def extract_text_from_pdf(pdf_file) -> str:
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
    pages = []
    for i, page in enumerate(pdf_reader.pages):
        text = page.extract_text()
        if text:
            pages.append(f"--- Page {i + 1} ---\n{text}")
    return "\n".join(pages)


def ask_claude(document_text: str, chat_history: list) -> str:
    client = get_client()
    if client is None:
        raise ValueError("No API key configured.")

    system_prompt = f"""You are a helpful document assistant.

The user has uploaded a document. Here is the full content:

{document_text}

Answer questions based ONLY on this document.
If the answer is not in the document, say clearly:
'I could not find this information in the document.'
Be concise and accurate."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=chat_history,
    )
    return message.content[0].text

# ============================================
# Header
# ============================================
st.title("SmartDocs")
st.caption("Upload a PDF and ask questions in plain English.")

# ============================================
# Step 1 — API Key input
# ============================================
with st.expander("🔑 API Key (optional — use your own Anthropic key)", expanded=not bool(get_client())):
    st.markdown('<div class="api-section">', unsafe_allow_html=True)
    user_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        value=st.session_state["api_key"],
        help="Your key is used only for this session and never stored.",
    )
    if user_key != st.session_state["api_key"]:
        st.session_state["api_key"] = user_key
        st.session_state["client"] = None  # reset cached client
    st.markdown("</div>", unsafe_allow_html=True)

# Verify we have a working key before going further
client = get_client()
if client is None:
    st.warning("No API key found. Enter your Anthropic API key above to get started.")
    st.stop()

# ============================================
# Step 3 — File upload with size validation
# ============================================
st.divider()
uploaded_file = st.file_uploader(
    "Upload a PDF document",
    type="pdf",
    help=f"Maximum file size: {MAX_FILE_SIZE_MB} MB",
)

if uploaded_file is not None:
    # Size check
    file_bytes = uploaded_file.getvalue()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        st.error(
            f"File is too large ({len(file_bytes) / 1024 / 1024:.1f} MB). "
            f"Please upload a PDF under {MAX_FILE_SIZE_MB} MB."
        )
        st.stop()

    # New file — parse it
    if uploaded_file.name != st.session_state["document_name"]:
        with st.spinner("Reading document..."):
            try:
                text = extract_text_from_pdf(uploaded_file)
                if not text.strip():
                    st.warning(
                        "No readable text found in this PDF. "
                        "It may be a scanned image — try a text-based PDF."
                    )
                    st.stop()
                st.session_state["document_text"] = text
                st.session_state["document_name"] = uploaded_file.name
                st.session_state["chat_history"] = []
            except Exception as e:
                st.error(f"Could not read PDF: {e}")
                st.stop()

    st.markdown(
        f'<div class="doc-badge">📄 {st.session_state["document_name"]}'
        f' &nbsp;·&nbsp; {len(file_bytes) / 1024:.0f} KB</div>',
        unsafe_allow_html=True,
    )

# ============================================
# Chat interface
# ============================================
if st.session_state["document_text"] is not None:

    with st.expander("Preview document text"):
        preview = st.session_state["document_text"][:800]
        st.text(preview + ("..." if len(st.session_state["document_text"]) > 800 else ""))

    st.subheader("Ask a question")

    # Render conversation
    for msg in st.session_state["chat_history"]:
        st.chat_message(msg["role"]).write(msg["content"])

    question = st.chat_input("Ask anything about this document…")

    if question:
        st.chat_message("user").write(question)
        st.session_state["chat_history"].append({"role": "user", "content": question})

        with st.spinner("Thinking…"):
            try:
                answer = ask_claude(
                    st.session_state["document_text"],
                    st.session_state["chat_history"],
                )
            except anthropic.AuthenticationError:
                st.error("Invalid API key. Please check the key you entered and try again.")
                st.session_state["chat_history"].pop()  # remove the unanswered question
                st.stop()
            except anthropic.RateLimitError:
                st.error("Rate limit reached. Wait a moment and try again.")
                st.session_state["chat_history"].pop()
                st.stop()
            except anthropic.APIStatusError as e:
                st.error(f"API error ({e.status_code}): {e.message}")
                st.session_state["chat_history"].pop()
                st.stop()
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.session_state["chat_history"].pop()
                st.stop()

        st.chat_message("assistant").write(answer)
        st.session_state["chat_history"].append({"role": "assistant", "content": answer})

    if st.session_state["chat_history"]:
        if st.button("Clear conversation", type="secondary"):
            st.session_state["chat_history"] = []
            st.rerun()
