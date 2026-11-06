
from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
import time
import ssl
import truststore


from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)
import pymupdf
from sqlalchemy.orm import Session
from backend.database.models.source import Source
from backend.database.models.source_fact import SourceFact, SourceSnapshot
from backend.database.models.verification import ReviewTask


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = PROJECT_ROOT / "data" / "source_snapshots"

MAX_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = 20
USER_AGENT = "SchemeSathiKnowledgeBot/1.0"


class UnsafeSourceURL(ValueError):
    pass


def canonical_url_hash(url: str) -> str:
    parsed = urlsplit(url.strip())
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = hostname if not port or port == 443 else f"{hostname}:{port}"
    canonical_url = urlunsplit(
        ("https", netloc, parsed.path or "/", parsed.query, "")
    )
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()


class SafeHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.skip_tags = {"script", "style", "noscript", "svg"}

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.skip_tags:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.skip_tags and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if not self.skip_depth:
            value = " ".join(data.split())
            if value:
                self.parts.append(value)


def validate_public_url(url: str) -> str:
    parsed = urlsplit(url)

    if parsed.scheme.lower() != "https":
        raise UnsafeSourceURL("Only HTTPS URLs are permitted.")

    if not parsed.hostname:
        raise UnsafeSourceURL("URL hostname is missing.")

    if parsed.username or parsed.password:
        raise UnsafeSourceURL("URL credentials are not permitted.")

    if parsed.port not in (None, 443):
        raise UnsafeSourceURL("Non-standard HTTPS ports are not permitted.")

    hostname = parsed.hostname.rstrip(".").lower()

    if hostname in {"localhost", "localhost.localdomain"}:
        raise UnsafeSourceURL("Localhost is not permitted.")

    try:
        addresses = socket.getaddrinfo(
            hostname,
            443,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise UnsafeSourceURL(
            f"Unable to resolve hostname: {hostname}"
        ) from exc

    if not addresses:
        raise UnsafeSourceURL("Hostname did not resolve.")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if not ip.is_global:
            raise UnsafeSourceURL(
                f"Non-public IP destination rejected: {ip}"
            )

    return url


class SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, original_hostname: str):
        super().__init__()
        self.redirect_count = 0
        self.original_hostname = original_hostname.rstrip(".").lower()

    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl,
    ):
        self.redirect_count += 1

        if self.redirect_count > MAX_REDIRECTS:
            raise UnsafeSourceURL("Too many redirects.")

        target = urljoin(req.full_url, newurl)
        target_hostname = (urlsplit(target).hostname or "").rstrip(".").lower()
        if target_hostname != self.original_hostname:
            raise UnsafeSourceURL(
                "Cross-host redirects are blocked. Review the destination host "
                "and register it through an explicit source-approval process."
            )
        validate_public_url(target)

        return super().redirect_request(
            req,
            fp,
            code,
            msg,
            headers,
            target,
        )


def fetch_page(url: str) -> dict:
    validate_public_url(url)

    original_hostname = (urlsplit(url).hostname or "").rstrip(".").lower()
    redirect_handler = SafeRedirectHandler(original_hostname)
    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    opener = build_opener(HTTPSHandler(context=ssl_context), redirect_handler)

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf",
        },
        method="GET",
    )

    with opener.open(request, timeout=REQUEST_TIMEOUT) as response:
        final_url = response.geturl()
        validate_public_url(final_url)
        content_type = response.headers.get_content_type()

        allowed_content_types = {
            "text/html",
            "application/xhtml+xml",
            "application/pdf",
        }
        if content_type not in allowed_content_types:
            raise ValueError(f"Unsupported content type: {content_type}")

        content = response.read(MAX_RESPONSE_BYTES + 1)
        if len(content) > MAX_RESPONSE_BYTES:
            raise ValueError("Source exceeds 10 MB limit.")

        encoding = response.headers.get_content_charset() or "utf-8"
        return {
            "content": content,
            "content_type": content_type,
            "status": response.status,
            "final_url": final_url,
            "encoding": encoding,
        }


def extract_page_text(content: bytes, encoding: str) -> str:
    decoded = content.decode(encoding, errors="replace")

    parser = SafeHTMLParser()
    parser.feed(decoded)
    return "\n".join(parser.parts)


def extract_pdf_text(content: bytes) -> str:
    """Extract actual selectable text from a PDF; never decode PDF bytes as text."""
    import fitz

    text_parts: list[str] = []
    with pymupdf.open(stream=content, filetype="pdf") as document:
        if document.page_count > 500:
            raise ValueError("PDF exceeds the 500-page extraction limit.")
        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text("text").strip()
            if page_text:
                text_parts.append(f"[Page {page_number}]\n{page_text}")
    return "\n\n".join(text_parts).strip()


def get_snapshot_paths(source_id: str, content_hash: str, content_type: str = "text/html"):
    directory = SNAPSHOT_DIR / str(source_id)
    directory.mkdir(parents=True, exist_ok=True)

    extension = "pdf" if content_type == "application/pdf" else "html"
    return (
        directory / f"{content_hash}.{extension}",
        directory / f"{content_hash}.txt",
    )


def create_source_freshness_review_tasks(db: Session, source_id: str, prior_snapshot_id: str | None) -> None:
    if prior_snapshot_id is None:
        return

    prior_facts = (
        db.query(SourceFact)
        .filter(SourceFact.source_snapshot_id == prior_snapshot_id)
        .all()
    )

    for fact in prior_facts:
        if fact.extraction_status in {"verified", "rejected"}:
            continue
        existing_task = (
            db.query(ReviewTask)
            .filter(
                ReviewTask.source_fact_id == fact.id,
                ReviewTask.task_type == "source_freshness_review",
                ReviewTask.status == "open",
            )
            .first()
        )
        if existing_task:
            continue
        db.add(
            ReviewTask(
                source_fact_id=fact.id,
                task_type="source_freshness_review",
                status="open",
                priority="high",
            )
        )


def ingest_source(db: Session, source: Source) -> dict:
    if not source.is_active:
        return {
            "source_id": str(source.id),
            "status": "skipped",
            "reason": "Source is inactive.",
        }

    now = datetime.now(timezone.utc)

    try:
        page = fetch_page(source.url)
        content = page["content"]
        content_hash = hashlib.sha256(content).hexdigest()

        latest_snapshot = (
            db.query(SourceSnapshot)
            .filter(SourceSnapshot.source_id == source.id)
            .order_by(SourceSnapshot.fetched_at.desc())
            .first()
        )

        if latest_snapshot and latest_snapshot.content_hash == content_hash:
            source.last_checked_at = now
            source.next_check_at = now + timedelta(hours=source.retrieval_interval_hours)
            db.commit()
            return {
                "source_id": str(source.id),
                "status": "unchanged",
                "snapshot_id": str(latest_snapshot.id),
                "content_hash": content_hash,
            }

        if page["content_type"] == "application/pdf":
            text_content = extract_pdf_text(content)
            extraction_status = "needs_ocr" if not text_content.strip() else "completed"
        else:
            text_content = extract_page_text(content, page["encoding"])
            extraction_status = "completed" if text_content.strip() else "failed"

        html_path, text_path = get_snapshot_paths(str(source.id), content_hash, page["content_type"])
        html_path.write_bytes(content)
        text_path.write_text(text_content, encoding="utf-8")

        snapshot = SourceSnapshot(
            source_id=source.id,
            fetched_at=now,
            content_hash=content_hash,
            content_type=page["content_type"],
            http_status=page["status"],
            storage_uri=html_path.relative_to(PROJECT_ROOT).as_posix(),
            extraction_status=extraction_status,
            extracted_at=now if extraction_status == "completed" else None,
        )

        db.add(snapshot)
        source.last_checked_at = now
        source.next_check_at = now + timedelta(hours=source.retrieval_interval_hours)
        if latest_snapshot and latest_snapshot.content_hash != content_hash:
            source.content_changed_at = now
            create_source_freshness_review_tasks(db, str(source.id), str(latest_snapshot.id))

        db.commit()
        db.refresh(snapshot)

        return {
            "source_id": str(source.id),
            "status": "ingested",
            "snapshot_id": str(snapshot.id),
            "content_hash": content_hash,
            "text_characters": len(text_content),
            "storage_uri": snapshot.storage_uri,
            "final_url": page["final_url"],
            "extraction_status": extraction_status,
        }

    except Exception as exc:
        db.rollback()
        source = db.query(Source).filter(Source.id == source.id).first()
        if source:
            source.last_checked_at = now
            source.next_check_at = now + timedelta(hours=min(source.retrieval_interval_hours, 6))
            db.commit()

        return {
            "source_id": str(source.id) if source else None,
            "status": "failed",
            "error": str(exc),
        }


def ingest_all_active_sources(db: Session) -> list[dict]:
    sources = (
        db.query(Source)
        .filter(Source.is_active.is_(True))
        .order_by(Source.created_at.asc())
        .all()
    )

    results = []

    for source in sources:
        results.append(ingest_source(db, source))

    return results
