import os

import streamlit as st
import anthropic
import PyPDF2
import io

# Initialize Claude client
#client = anthropic.Anthropic()

#for streamlit cloud deployment, we use st.secrets to securely store the API key
client = anthropic.Anthropic(
    api_key=st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
)

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file"""
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
    text = ""
    for page_num, page in enumerate(pdf_reader.pages):
        page_text = page.extract_text()
        if page_text:
            text += f"\n--- Page {page_num + 1} ---\n"
            text += page_text
    return text

def ask_claude(document_text, question, chat_history):
    """Send document + conversation history to Claude"""
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
        messages=chat_history
    )
    return message.content[0].text

# ============================================
# UI
# ============================================
st.title("SmartDocs — Ask Your Documents")
st.write("Upload a PDF and ask questions in plain English.")

# Initialize session state
if 'document_text' not in st.session_state:
    st.session_state['document_text'] = None
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'document_name' not in st.session_state:
    st.session_state['document_name'] = None

# File upload
uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file is not None:
    if uploaded_file.name != st.session_state['document_name']:
        with st.spinner("Reading document..."):
            st.session_state['document_text'] = extract_text_from_pdf(uploaded_file)
            st.session_state['document_name'] = uploaded_file.name
            st.session_state['chat_history'] = []
        st.success(f"✅ Loaded: {uploaded_file.name}")

if st.session_state['document_text'] is not None:

    st.divider()

    with st.expander("📄 Preview document text"):
        st.write(st.session_state['document_text'][:800] + "...")

    st.subheader("💬 Ask Questions")

    # Display chat history
    for message in st.session_state['chat_history']:
        if message['role'] == 'user':
            st.chat_message("user").write(message['content'])
        else:
            st.chat_message("assistant").write(message['content'])

    # Question input
    question = st.chat_input("Ask a question about your document...")

    if question:
        st.chat_message("user").write(question)

        st.session_state['chat_history'].append({
            "role": "user",
            "content": question
        })

        with st.spinner("Thinking..."):
            answer = ask_claude(
                st.session_state['document_text'],
                question,
                st.session_state['chat_history']
            )

        st.chat_message("assistant").write(answer)

        st.session_state['chat_history'].append({
            "role": "assistant",
            "content": answer
        })

    if st.button("🗑️ Clear Conversation"):
        st.session_state['chat_history'] = []
        st.rerun()