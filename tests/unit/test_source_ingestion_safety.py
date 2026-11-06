from types import SimpleNamespace

import fitz
import pytest

from backend.services.fact_extraction import (
    extract_selected_snapshot_facts,
    resolve_snapshot_text_path,
)
from backend.services.source_ingestion import (
    SafeRedirectHandler,
    UnsafeSourceURL,
    extract_pdf_text,
)


def make_pdf(text: str | None = None) -> bytes:
    document = fitz.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def test_pdf_extraction_reads_real_pdf_text():
    extracted = extract_pdf_text(
        make_pdf("Applicants must submit proof of identity.")
    )
    assert "[Page 1]" in extracted
    assert "Applicants must submit proof of identity." in extracted


def test_pdf_extraction_returns_empty_for_image_only_or_blank_pdf():
    assert extract_pdf_text(make_pdf()) == ""


def test_cross_host_redirect_is_rejected_before_network_resolution():
    handler = SafeRedirectHandler("example.gov.in")
    request = SimpleNamespace(full_url="https://example.gov.in/start")

    with pytest.raises(UnsafeSourceURL, match="Cross-host redirects are blocked"):
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://external.example/document.pdf",
        )


def test_pdf_snapshot_uri_resolves_companion_text_file(tmp_path, monkeypatch):
    from backend.services import fact_extraction

    snapshot_root = fact_extraction.PROJECT_ROOT / "data" / "source_snapshots"
    test_dir = snapshot_root / "pdf-path-test"
    test_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = test_dir / "sample.pdf"
    text_path = test_dir / "sample.txt"
    text_path.write_text("A sufficiently long extracted fact sentence.", encoding="utf-8")
    try:
        resolved = resolve_snapshot_text_path(
            "data/source_snapshots/pdf-path-test/sample.pdf"
        )
        assert resolved == text_path.resolve()
    finally:
        text_path.unlink(missing_ok=True)
        pdf_path.unlink(missing_ok=True)
        test_dir.rmdir()


def test_fact_extraction_requires_explicit_scope():
    with pytest.raises(ValueError, match="Select snapshots"):
        extract_selected_snapshot_facts(db=None)
