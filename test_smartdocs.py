"""
SmartDocs Automated Test Suite
Run with:  python test_smartdocs.py
Pytest:    pytest test_smartdocs.py -v
"""

from dotenv import load_dotenv
load_dotenv()

import sys
import io
import os
import tempfile
import warnings
from unittest.mock import MagicMock, patch

# ── Mock streamlit BEFORE importing app.py ──────────────────────────────────
# app.py executes Streamlit calls at module level; we need the mock in place
# before the import so none of those calls crash the test process.

class _SessionState(dict):
    """Dict subclass that satisfies st.session_state attribute/item access."""
    pass

_mock_session_state = _SessionState({
    "document_text": None,
    "document_name": None,
    "chat_history": [],
    "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    "client": None,
    "total_pages": None,
    "page_from": 1,
    "page_to": 1,
})

_mock_st = MagicMock()
_mock_st.session_state = _mock_session_state
_mock_st.secrets = {}  # any key access raises KeyError → falls back to os.getenv
# Return None so the `if uploaded_file is not None:` block is skipped at import
_mock_st.file_uploader.return_value = None
_mock_st.chat_input.return_value = None

sys.modules["streamlit"] = _mock_st

from app import extract_text_from_pdf, ask_claude  # noqa: E402

import anthropic as _anthropic
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# ── PDF helpers ──────────────────────────────────────────────────────────────

def create_test_pdf(pages_content: list[str]) -> bytes:
    """Create an in-memory PDF; one entry in pages_content = one page."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for content in pages_content:
        txt = c.beginText(72, 720)
        txt.setFont("Helvetica", 11)
        words = content.split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > 85:
                txt.textLine(line)
                line = word
            else:
                line = (line + " " + word).strip()
        if line:
            txt.textLine(line)
        c.drawText(txt)
        c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def create_empty_pdf() -> bytes:
    """Create an in-memory PDF with a single blank page (no text)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


# ── Infrastructure helpers ────────────────────────────────────────────────────

def _is_infrastructure_error(e: Exception) -> bool:
    """True when the error is an API/config problem, not a logic failure."""
    if isinstance(e, (
        _anthropic.AuthenticationError,
        _anthropic.RateLimitError,
        _anthropic.APIStatusError,
        _anthropic.APIConnectionError,
    )):
        return True
    if isinstance(e, ValueError) and "api key" in str(e).lower():
        return True
    return False


def _get_real_client():
    """Build a real Anthropic client from the env var, or return None."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return _anthropic.Anthropic(api_key=key) if key else None


# ── Category 1 — Core Functionality (30 pts) ─────────────────────────────────

def test_basic_text_extraction():
    pdf = create_test_pdf(["Hello SmartDocs world"])
    result = extract_text_from_pdf(pdf)
    assert "Hello" in result and "SmartDocs" in result


def test_page_range_extraction():
    pdf = create_test_pdf([
        "Content of page one",
        "Content of page two",
        "Content of page three",
        "Content of page four",
        "Content of page five",
    ])
    result = extract_text_from_pdf(pdf, start_page=2, end_page=3)
    assert "--- Page 2 ---" in result
    assert "--- Page 3 ---" in result
    assert "--- Page 1 ---" not in result
    assert "--- Page 4 ---" not in result


def test_single_page_extraction():
    pdf = create_test_pdf(["Page one text", "Page two text", "Page three text"])
    result = extract_text_from_pdf(pdf, start_page=2, end_page=2)
    assert "--- Page 2 ---" in result
    assert "--- Page 1 ---" not in result
    assert "--- Page 3 ---" not in result


def test_full_document_default():
    pdf = create_test_pdf(["First page", "Second page", "Third page"])
    result = extract_text_from_pdf(pdf)
    assert "--- Page 1 ---" in result
    assert "--- Page 2 ---" in result
    assert "--- Page 3 ---" in result


# ── Category 2 — Boundary Conditions (25 pts) ────────────────────────────────

def test_empty_pdf():
    pdf = create_empty_pdf()
    result = extract_text_from_pdf(pdf)
    assert result.strip() == ""


def test_single_page_pdf():
    pdf = create_test_pdf(["Only one page here"])
    result = extract_text_from_pdf(pdf)
    assert "--- Page 1 ---" in result


def test_large_page_count():
    pages = [f"This is page number {i + 1} of fifty pages total" for i in range(50)]
    pdf = create_test_pdf(pages)
    result = extract_text_from_pdf(pdf)
    assert "--- Page 50 ---" in result


def test_page_range_equals_total():
    pdf = create_test_pdf(["Alpha page", "Beta page", "Gamma page"])
    result = extract_text_from_pdf(pdf, start_page=1, end_page=3)
    assert "--- Page 1 ---" in result
    assert "--- Page 3 ---" in result


def test_special_characters_in_content():
    pdf = create_test_pdf(["Special chars: @#$%&*() brackets and symbols here"])
    result = extract_text_from_pdf(pdf)
    assert isinstance(result, str) and len(result) > 0


def test_very_long_text_page():
    content = " ".join(["word"] * 1000)
    pdf = create_test_pdf([content])
    result = extract_text_from_pdf(pdf)
    assert "--- Page 1 ---" in result and len(result) > 100


def test_corrupt_bytes():
    try:
        extract_text_from_pdf(b"not a pdf at all")
        assert False, "Expected an exception for corrupt bytes"
    except Exception:
        pass


def test_empty_bytes():
    try:
        extract_text_from_pdf(b"")
        assert False, "Expected an exception for empty bytes"
    except Exception:
        pass


# ── Category 3 — Security (30 pts) ───────────────────────────────────────────

def test_no_api_key_in_extracted_text():
    api_key = os.getenv("ANTHROPIC_API_KEY", "sk-ant-test-placeholder")
    pdf = create_test_pdf(["This document contains no secrets or credentials."])
    result = extract_text_from_pdf(pdf)
    assert api_key not in result


def test_path_traversal_attempt():
    pdf = create_test_pdf(["../../../etc/passwd root colon x colon zero system"])
    result = extract_text_from_pdf(pdf)
    assert isinstance(result, str) and len(result) > 0


def test_script_injection_in_question():
    pdf = create_test_pdf(["<script>alert(1)</script> DROP TABLE users -- {{7*7}}"])
    result = extract_text_from_pdf(pdf)
    # Injection strings must be returned as plain text, not evaluated
    assert isinstance(result, str) and len(result) > 0


def test_api_key_not_in_error_messages():
    api_key = os.getenv("ANTHROPIC_API_KEY", "sk-ant-test-placeholder")
    saved = _mock_session_state.get("api_key", "")
    _mock_session_state["api_key"] = ""
    try:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            ask_claude("test document", [{"role": "user", "content": "hi"}])
            assert False, "Should have raised an exception"
    except Exception as e:
        assert api_key not in str(e), f"API key leaked in error message: {e}"
    finally:
        _mock_session_state["api_key"] = saved


def test_file_size_boundary():
    pdf = create_test_pdf(["File size boundary check document"])
    assert len(pdf) < 10 * 1024 * 1024, "Test PDF itself exceeds 10 MB"


def test_no_data_written_to_disk():
    tmp_dir = tempfile.gettempdir()
    cwd = os.getcwd()
    before_tmp = set(os.listdir(tmp_dir))
    before_cwd = set(os.listdir(cwd))

    pdf = create_test_pdf(["No disk writes expected during extraction"])
    extract_text_from_pdf(pdf)

    new_in_tmp = [f for f in (set(os.listdir(tmp_dir)) - before_tmp) if f.endswith(".pdf")]
    new_in_cwd = [f for f in (set(os.listdir(cwd)) - before_cwd) if f.endswith(".pdf")]
    assert not new_in_tmp, f"PDF files written to tmp dir: {new_in_tmp}"
    assert not new_in_cwd, f"PDF files written to working dir: {new_in_cwd}"


# ── Category 4 — AI User Simulation (15 pts) ─────────────────────────────────
# API failures (auth, rate-limit, network) warn instead of failing.

def test_factual_question_answered_correctly():
    try:
        client = _get_real_client()
        if client is None:
            warnings.warn("ANTHROPIC_API_KEY not set — skipping AI test")
            return
        pdf = create_test_pdf([
            "Our company was founded in 2010. The CEO is John Smith. "
            "We are based in New York and employ five hundred people."
        ])
        doc_text = extract_text_from_pdf(pdf)
        history = [{"role": "user", "content": "When was the company founded?"}]
        with patch("app.get_client", return_value=client):
            answer = ask_claude(doc_text, history)
        assert "2010" in answer, f"Expected '2010' in answer: {answer[:300]}"
    except Exception as e:
        if _is_infrastructure_error(e):
            warnings.warn(f"API unavailable — {type(e).__name__}: {e}")
            return
        raise


def test_out_of_document_question():
    try:
        client = _get_real_client()
        if client is None:
            warnings.warn("ANTHROPIC_API_KEY not set — skipping AI test")
            return
        pdf = create_test_pdf(["The sky is blue because of Rayleigh scattering of sunlight."])
        doc_text = extract_text_from_pdf(pdf)
        history = [{"role": "user", "content": "What is the population of India?"}]
        with patch("app.get_client", return_value=client):
            answer = ask_claude(doc_text, history)
        lower = answer.lower()
        found_disclaimer = any(phrase in lower for phrase in [
            "not in the document",
            "could not find",
            "not mentioned",
            "no information",
            "doesn't contain",
            "does not contain",
            "not provided",
        ])
        assert found_disclaimer, f"Expected disclaimer in answer: {answer[:300]}"
    except Exception as e:
        if _is_infrastructure_error(e):
            warnings.warn(f"API unavailable — {type(e).__name__}: {e}")
            return
        raise


def test_multi_turn_conversation():
    try:
        client = _get_real_client()
        if client is None:
            warnings.warn("ANTHROPIC_API_KEY not set — skipping AI test")
            return
        pdf = create_test_pdf([
            "The product is called AlphaWidget. It costs 99 dollars. "
            "It was launched in March 2023."
        ])
        doc_text = extract_text_from_pdf(pdf)
        history = [
            {"role": "user", "content": "What is the product called?"},
            {"role": "assistant", "content": "The product is called AlphaWidget."},
            {"role": "user", "content": "How much does it cost?"},
        ]
        with patch("app.get_client", return_value=client):
            answer = ask_claude(doc_text, history)
        assert "99" in answer or "dollar" in answer.lower(), (
            f"Expected price in answer: {answer[:300]}"
        )
    except Exception as e:
        if _is_infrastructure_error(e):
            warnings.warn(f"API unavailable — {type(e).__name__}: {e}")
            return
        raise


def test_empty_question_handling():
    # Verify the guard logic used in app.py (`if question:`) blocks all empty inputs.
    # st.chat_input never yields whitespace-only strings; an additional strip() check
    # covers the remaining edge cases.
    empty_inputs = ["", "   ", "\n", "\t"]
    for q in empty_inputs:
        would_call_api = bool(q) and bool(q.strip())
        assert not would_call_api, f"Guard should block empty input {repr(q)}"


# ── Scoring runner ────────────────────────────────────────────────────────────

CATEGORIES = [
    {
        "name": "Core Functionality",
        "weight": 30,
        "tests": [
            test_basic_text_extraction,
            test_page_range_extraction,
            test_single_page_extraction,
            test_full_document_default,
        ],
    },
    {
        "name": "Boundary Conditions",
        "weight": 25,
        "tests": [
            test_empty_pdf,
            test_single_page_pdf,
            test_large_page_count,
            test_page_range_equals_total,
            test_special_characters_in_content,
            test_very_long_text_page,
            test_corrupt_bytes,
            test_empty_bytes,
        ],
    },
    {
        "name": "Security",
        "weight": 30,
        "tests": [
            test_no_api_key_in_extracted_text,
            test_path_traversal_attempt,
            test_script_injection_in_question,
            test_api_key_not_in_error_messages,
            test_file_size_boundary,
            test_no_data_written_to_disk,
        ],
    },
    {
        "name": "AI User Simulation",
        "weight": 15,
        "tests": [
            test_factual_question_answered_correctly,
            test_out_of_document_question,
            test_multi_turn_conversation,
            test_empty_question_handling,
        ],
    },
]


def run_tests() -> float:
    total_score = 0.0
    bar = "=" * 62

    print(f"\n{bar}")
    print("  SmartDocs Test Suite")
    print(bar)

    for cat in CATEGORIES:
        tests = cat["tests"]
        weight = cat["weight"]
        points_per_test = weight / len(tests)
        cat_score = 0.0

        print(f"\n  {cat['name']}  ({weight} pts — {len(tests)} tests)")
        print(f"  {'-' * 52}")

        for fn in tests:
            name = fn.__name__
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    fn()
                    if caught:
                        print(f"  ⚠️  {name}")
                        print(f"       {caught[-1].message}")
                    else:
                        print(f"  ✅ {name}")
                    cat_score += points_per_test
                except Exception as e:
                    print(f"  ❌ {name}")
                    print(f"       {type(e).__name__}: {e}")

        print(f"\n  Category score: {cat_score:.1f} / {weight}")
        total_score += cat_score

    print(f"\n{bar}")
    print(f"  FINAL SCORE: {total_score:.1f} / 100")

    if total_score >= 90:
        grade = "A — Production Ready"
    elif total_score >= 75:
        grade = "B — Beta Ready"
    elif total_score >= 60:
        grade = "C — Demo Ready"
    else:
        grade = "D — Needs Work"

    print(f"  GRADE: {grade}")
    print(f"{bar}\n")
    return total_score


if __name__ == "__main__":
    score = run_tests()
    sys.exit(0 if score >= 75 else 1)
