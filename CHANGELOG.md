# SmartDocs Changelog

All notable changes to SmartDocs are documented here.
Format: Version · Date · What changed and why.

---

## [V2.0] - 2026-04-29

### Added
- API key input field — users can now bring their 
  own Anthropic key. App no longer depends solely 
  on developer's key.
- File size validation — PDFs over 10MB are rejected 
  with a clear error message before processing begins.
- Scanned PDF detection — app detects image-only PDFs 
  and shows helpful guidance instead of returning 
  empty results.
- Page config — proper browser tab title, favicon, 
  and centered layout.
- Custom CSS — rounded corners, card-style API section,
  document badge showing filename and size.
- Specific error handling per error type:
  - AuthenticationError → invalid key message
  - RateLimitError → wait and retry message
  - APIStatusError → error code shown
  - Generic Exception → safe fallback message

### Improved
- Session state initialization — cleaner dictionary 
  pattern instead of repeated if/not-in checks.
- API key resolution — smart fallback chain:
  user input → Streamlit secrets → .env file
- PDF extraction — page numbers added to extracted 
  text for better context.
- Error recovery — failed questions removed from 
  chat history to prevent broken conversation state.

### Fixed
- App no longer crashes with red error screen on 
  API failures — all errors show friendly messages.
- Deployment fixed — app now works both locally 
  and on Streamlit Cloud without code changes.

---

## [V1.0] - 2026-04-28

### Added
- Initial working version of SmartDocs.
- PDF upload and text extraction using PyPDF2.
- Multi-turn conversation with Claude claude-sonnet-4-20250514.
- Chat history maintained across questions in same session.
- Session state — document and conversation persist 
  across Streamlit reruns.
- Clear conversation button.
- Document text preview expander.
- Deployed live on Streamlit Cloud.

### Technical Foundation
- Python + Streamlit + Anthropic SDK
- Context stuffing approach — full PDF text sent 
  with every API call.
- Stateless API handled via manual history management.
- Environment variables via python-dotenv locally,
  Streamlit secrets on cloud deployment.

---

## [V3.0] - Upcoming

### Planned
- Page range selection — users choose which pages 
  to process from large documents.
- Better large file error message — links to free 
  compression tools.
- OCR support for image-based PDFs (researching).

---

## Version Philosophy

```
V1 → Working prototype. Core function only.
V2 → Production ready. Error handling + security.
V3 → User experience. Power features.
V4 → Scale. Multiple docs, user accounts.
```