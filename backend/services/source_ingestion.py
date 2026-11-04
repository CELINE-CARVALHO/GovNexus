
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
from urllib.parse import urljoin, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)

from sqlalchemy.orm import Session
from backend.database.models.source import Source
from backend.database.models.source_fact import SourceSnapshot


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = PROJECT_ROOT / "data" / "source_snapshots"

MAX_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = 20
USER_AGENT = "SchemeSathiKnowledgeBot/1.0"


class UnsafeSourceURL(ValueError):
    pass


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
    def __init__(self):
        super().__init__()
        self.redirect_count = 0

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

    redirect_handler = SafeRedirectHandler()

    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    opener = build_opener(
        HTTPSHandler(context=ssl_context),
        redirect_handler,
    )

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )

    with opener.open(request, timeout=REQUEST_TIMEOUT) as response:
        final_url = response.geturl()

        validate_public_url(final_url)

        content_type = response.headers.get_content_type()

        if content_type not in {
            "text/html",
            "application/xhtml+xml",
        }:
            raise ValueError(
                f"Unsupported content type: {content_type}"
            )

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


def get_snapshot_paths(source_id: str, content_hash: str):
    directory = SNAPSHOT_DIR / str(source_id)
    directory.mkdir(parents=True, exist_ok=True)

    return (
        directory / f"{content_hash}.html",
        directory / f"{content_hash}.txt",
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

        existing = (
            db.query(SourceSnapshot)
            .filter(
                SourceSnapshot.source_id == source.id,
                SourceSnapshot.content_hash == content_hash,
            )
            .first()
        )

        if existing:
            source.last_checked_at = now
            source.next_check_at = now + timedelta(
                hours=source.retrieval_interval_hours
            )
            db.commit()

            return {
                "source_id": str(source.id),
                "status": "unchanged",
                "snapshot_id": str(existing.id),
                "content_hash": content_hash,
            }

        text_content = extract_page_text(
            content,
            page["encoding"],
        )

        html_path, text_path = get_snapshot_paths(
            str(source.id),
            content_hash,
        )

        html_path.write_bytes(content)
        text_path.write_text(
            text_content,
            encoding="utf-8",
        )

        snapshot = SourceSnapshot(
            source_id=source.id,
            fetched_at=now,
            content_hash=content_hash,
            content_type=page["content_type"],
            http_status=page["status"],
            storage_uri=html_path.relative_to(
                PROJECT_ROOT
            ).as_posix(),
            extraction_status="completed",
            extracted_at=now,
        )

        db.add(snapshot)

        source.last_checked_at = now
        source.next_check_at = now + timedelta(
            hours=source.retrieval_interval_hours
        )

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
        }

    except Exception as exc:
        db.rollback()

        source = (
            db.query(Source)
            .filter(Source.id == source.id)
            .first()
        )

        if source:
            source.last_checked_at = now
            source.next_check_at = now + timedelta(
                hours=min(
                    source.retrieval_interval_hours,
                    6,
                )
            )
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
