from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
import anthropic
import io

# ============================================
# Config
# ============================================
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

st.set_page_config(
    page_title="SmartDocs — AI Document Assistant",
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
    "total_pages": None,
    "page_from": 1,
    "page_to": 1,
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

def extract_text_from_pdf(
    file_bytes: bytes,
    start_page: int = 1,
    end_page: int = None
) -> str:
    """Extract and clean text from a page range (1-indexed, inclusive)."""
    import re
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    if end_page is None:
        end_page = len(pdf_reader.pages)
    pages = []
    for i in range(start_page - 1, end_page):
        text = pdf_reader.pages[i].extract_text()
        if text:
            # Fix single character per line issue
            # Join lines that are too short (less than 3 chars)
            lines = text.split('\n')
            cleaned_lines = []
            buffer = ""
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    if buffer:
                        cleaned_lines.append(buffer.strip())
                        buffer = ""
                    cleaned_lines.append("")
                elif len(stripped) <= 2:
                    # Short fragment — likely broken word, join it
                    buffer += stripped + " "
                else:
                    if buffer:
                        buffer += stripped + " "
                        # If buffer is now long enough flush it
                        if len(buffer) > 20:
                            cleaned_lines.append(buffer.strip())
                            buffer = ""
                    else:
                        cleaned_lines.append(stripped)
            if buffer:
                cleaned_lines.append(buffer.strip())

            # Remove multiple blank lines
            text = '\n'.join(cleaned_lines)
            text = re.sub(r'\n{3,}', '\n\n', text)
            # Fix multiple spaces
            text = re.sub(r' {2,}', ' ', text)

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
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=chat_history,
    )
    return message.content[0].text

# ============================================
# Header
# ============================================
st.title("SmartDocs AI")
st.caption("Upload any PDF. Ask questions. Get instant answers.")

# ============================================
# Step 1 — API Key input
# ============================================
with st.expander("🔑 API Key (optional — use your own Anthropic key)", expanded=not bool(get_client())):
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
    st.caption(
        "🔒 Your documents are never stored. "
        "Processed in real-time and discarded. "
        "Anthropic does not train on API data. "
        "[Learn more](https://anthropic.com/privacy)"
    )

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
    file_size_mb = len(file_bytes) / 1024 / 1024
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        st.error(
            f"File is too large ({file_size_mb:.1f} MB). "
            f"Please upload a PDF under {MAX_FILE_SIZE_MB} MB."
        )
        st.info(
            "Need to compress your PDF? Try these free tools:\n\n"
            "- [SmallPDF](https://smallpdf.com)\n"
            "- [ILovePDF](https://www.ilovepdf.com)"
        )
        st.stop()

    # New file — get total pages and reset range
    if uploaded_file.name != st.session_state["document_name"]:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        total_pages = len(pdf_reader.pages)
        st.session_state["total_pages"] = total_pages
        st.session_state["document_name"] = uploaded_file.name
        st.session_state["page_from"] = 1
        st.session_state["page_to"] = total_pages
        st.session_state["document_text"] = None
        st.session_state["chat_history"] = []

    total_pages = st.session_state["total_pages"]
    st.write(f"Total pages: **{total_pages}**")

    col1, col2 = st.columns(2)
    with col1:
        page_from = st.number_input(
            "From page", min_value=1, max_value=total_pages,
            value=st.session_state["page_from"],
        )
    with col2:
        page_to = st.number_input(
            "To page", min_value=1, max_value=total_pages,
            value=st.session_state["page_to"],
        )

    if page_from > page_to:
        st.error("'From page' must be less than or equal to 'To page'.")
        st.stop()

    # Re-extract when range changes or text not yet loaded
    range_changed = (
        page_from != st.session_state["page_from"]
        or page_to != st.session_state["page_to"]
    )
    if st.session_state["document_text"] is None or range_changed:
        st.session_state["page_from"] = page_from
        st.session_state["page_to"] = page_to
        if range_changed:
            st.session_state["chat_history"] = []
        with st.spinner("Reading document..."):
            try:
                text = extract_text_from_pdf(file_bytes, page_from, page_to)
                if not text.strip():
                    st.warning(
                        "No readable text found in this PDF. "
                        "It may be a scanned image — try a text-based PDF."
                    )
                    st.stop()
                st.session_state["document_text"] = text
            except Exception as e:
                st.error(f"Could not read PDF: {e}")
                st.stop()

    file_size_kb = len(file_bytes) / 1024
    st.caption(
        f"📄 {st.session_state['document_name']} "
        f"· Pages {st.session_state['page_from']}–{st.session_state['page_to']} "
        f"· {file_size_kb:.0f} KB"
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


# ============================================
# Footer
# ============================================
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #6b7280; 
    font-size: 0.8rem; padding: 10px'>
        Built by <a href='https://www.linkedin.com/in/sumit-sharma-dev' 
        target='_blank' style='color: #6b7280'>Sumit Sharma</a> · 
        <a href='https://github.com/SumitSharmaRepository/smartdocs' 
        target='_blank' style='color: #6b7280'>GitHub</a> · 
        © 2026 SmartDocs
    </div>
    """,
    unsafe_allow_html=True
)