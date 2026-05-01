# SmartDocs — Claude Code Instructions

## Project Overview
SmartDocs is an AI-powered PDF Q&A tool built with 
Python, Streamlit, and Anthropic Claude API.
Users upload PDFs and ask questions in plain English.

## Tech Stack
- Python 3.11
- Streamlit 1.56
- Anthropic Python SDK 0.97
- PyPDF2 for PDF parsing
- python-dotenv for local environment variables

## Project Structure
smartdocs/
├── app.py           ← main application, all code here
├── .env             ← never touch, never read, never expose
├── .gitignore       ← never modify
├── requirements.txt ← update when adding new packages
└── CLAUDE.md        ← this file

## Critical Rules — Never Break These

### API Key Handling
The API key resolution follows this exact priority:
1. User-entered key from st.session_state["api_key"]
2. st.secrets["ANTHROPIC_API_KEY"] for Streamlit Cloud
3. os.getenv("ANTHROPIC_API_KEY") for local .env

NEVER hardcode API keys.
NEVER change this priority order.
NEVER expose keys in logs or error messages.

### Session State
These session state keys must always exist:
- document_text: extracted PDF text or None
- document_name: uploaded filename or None  
- chat_history: list of message dicts
- api_key: user-entered key string
- client: Anthropic client or None

NEVER rename these keys.
NEVER remove them from the defaults dict.

### Chat History Format
Chat history must always follow this exact format:
{"role": "user" or "assistant", "content": "string"}

NEVER add extra keys to message dicts.
Claude API will reject non-standard formats.

### Error Handling Pattern
Every API call must catch these in this order:
1. anthropic.AuthenticationError
2. anthropic.RateLimitError  
3. anthropic.APIStatusError
4. Exception (generic fallback)

After each error:
- Show st.error() with friendly message
- pop() the last chat_history item
- Call st.stop()

NEVER show raw exception messages to users.
NEVER skip the pop() after an error.

### st.stop() Usage
Always call st.stop() after:
- Any validation failure
- Any error that prevents proceeding
- File size exceeded
- No API key found

## Code Style
- Use f-strings for string formatting
- Use type hints on function signatures
- Add docstrings to all functions
- Keep functions small and single-purpose
- Constants in UPPERCASE at top of file
- Comments above each major section

## Streamlit Conventions
- st.set_page_config() must be first Streamlit call
- Use st.spinner() for any operation over 1 second
- Use st.columns() for side-by-side layouts
- Use st.expander() for optional/advanced content
- Use st.divider() between major sections

## What To Never Do
- Never use st.experimental_ functions (deprecated)
- Never store sensitive data in session_state visibly
- Never make API calls outside try/except blocks
- Never modify .env or .gitignore
- Never add print() statements (use st.write for debug)
- Never break existing error handling

## When Adding New Features
1. Add new session state keys to the defaults dict
2. Follow existing error handling pattern
3. Update requirements.txt if adding new packages
4. Keep all code in app.py unless told otherwise
5. Test locally before suggesting deployment

## Current Features (Do Not Break)
- API key input with fallback chain
- PDF upload with 10MB size limit
- Scanned PDF detection
- Multi-turn conversation with history
- Specific error handling per error type
- Clear conversation button