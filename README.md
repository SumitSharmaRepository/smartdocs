# SmartDocs — Ask Your Documents

# SmartDocs AI
### Built by [Sumit Sharma](https://www.linkedin.com/in/sumit-sharma-dev)

> Upload any PDF. Ask questions. Get instant answers.
> Powered by Claude AI.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with Python](https://img.shields.io/badge/Built%20with-Python-blue)](https://python.org)
[![Powered by Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-orange)](https://anthropic.com)

Upload any PDF and ask questions in plain English. 
Powered by Claude AI.

## 🌐 Live Demo
👉 [Try SmartDocs](https://asksmartdocs-ai.streamlit.app)

## 🎥 Demo
![alt text](image.png)
## smart-docs V2
<img width="1076" height="490" alt="image" src="https://github.com/user-attachments/assets/aeeceb52-8a00-4a26-a830-5ef142410ae0" />
## smart-docs V3
<img width="721" height="791" alt="image" src="https://github.com/user-attachments/assets/3a679578-679a-4442-be65-624f3985889c" />


## What It Does
- Upload any PDF document (up to 10MB)
- Select a page range to focus on specific sections
- Ask questions in plain English
- Get accurate answers instantly
- Full multi-turn conversation memory
- Remembers context across multiple questions
- Bring your own Anthropic API key or use the built-in one

## V3 Highlights
- **Page range selection** — process only the pages you need
- **Smart re-extraction** — PDF only re-read when range changes
- **Better file errors** — oversized files link to free compression tools
- **Privacy notice** — clear reassurance before entering your API key
- **10MB upload limit** enforced at the Streamlit config level

## Tech Stack
- Python
- Claude API (Anthropic)
- Streamlit
- PyPDF2

## Built By
Sumit Sharma — Senior Full Stack Engineer
[LinkedIn](https://www.linkedin.com/in/sumit-sharma-dev)

## Run Locally
1. Clone the repo
2. Install dependencies:
   pip install -r requirements.txt
3. Create .env file:
   ANTHROPIC_API_KEY=your-key-here
4. Run:
   streamlit run app.py

## Use Cases
- CA firms querying financial documents
- Law offices searching case files
- Coaching institutes answering student queries
- Any business with document-heavy workflows
