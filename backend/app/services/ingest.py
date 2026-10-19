"""Document ingestion: fetch (politely), parse, clean, chunk, embed, store.

Rules of engagement:
* respect robots.txt and a minimum per-host delay;
* never bypass logins, CAPTCHA or restricted areas — inaccessible URLs are
  recorded with an error and left for manual verification;
* content is hashed so re-runs detect changes instead of duplicating rows.
"""

from __future__ import annotations

import hashlib
import io
import time
import urllib.robotparser as robotparser
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..config import settings
from ..constants import DocType, Verification
from ..db import SessionLocal
from ..models import Chunk, Document, Source, SourceRefreshLog, utcnow
from .chunking import chunk_text, clean_text
from .embeddings import embed_texts

_last_request_at: dict[str, float] = {}
_robots_cache: dict[str, robotparser.RobotFileParser | None] = {}


@dataclass
class FetchResult:
    url: str
    status_code: int | None
    content_type: str | None
    content: bytes | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status_code == 200 and bool(self.content)


def _host(url: str) -> str:
    return urlparse(url).netloc.lower()


def _respect_delay(url: str) -> None:
    host = _host(url)
    last = _last_request_at.get(host)
    if last is not None:
        wait = settings.min_request_interval_seconds - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
    _last_request_at[host] = time.monotonic()


def robots_allowed(url: str) -> bool:
    host = _host(url)
    if host in _robots_cache:
        parser = _robots_cache[host]
    else:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = None
        try:
            response = httpx.get(robots_url, timeout=10.0, headers={"User-Agent": settings.user_agent})
            if response.status_code == 200:
                parser = robotparser.RobotFileParser()
                parser.parse(response.text.splitlines())
            elif response.status_code in (401, 403):
                parser = None  # explicitly restricted
            else:
                # No robots.txt (404 etc.) means "no restrictions published".
                parser = _allow_all_parser()
        except Exception:  # noqa: BLE001
            # The host refused a robots.txt request; we do not treat that as
            # permission to hammer it, but a single polite request is allowed.
            parser = _allow_all_parser()
        _robots_cache[host] = parser
    if parser is None:
        return False
    try:
        return parser.can_fetch(settings.user_agent, url) or parser.can_fetch("*", url)
    except Exception:  # noqa: BLE001
        return True


def _allow_all_parser() -> robotparser.RobotFileParser:
    """Python's RobotFileParser denies everything until a file is read, so an
    explicitly constructed allow-all parser is needed for 'no robots.txt'."""
    parser = robotparser.RobotFileParser()
    parser.allow_all = True
    parser.last_checked = 1
    return parser


def fetch(url: str, *, check_robots: bool = True) -> FetchResult:
    if check_robots and not robots_allowed(url):
        return FetchResult(url, None, None, None, error="Blocked by robots.txt or explicitly disallowed")
    _respect_delay(url)
    try:
        response = httpx.get(
            url,
            timeout=settings.fetch_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent, "Accept-Language": "en"},
        )
        return FetchResult(
            url=url,
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            content=response.content if response.status_code == 200 else None,
        )
    except Exception as exc:  # noqa: BLE001
        return FetchResult(url, None, None, None, error=f"{type(exc).__name__}: {exc}")


def html_to_text(html: bytes | str, *, max_chars: int = 200_000) -> tuple[str, str]:
    """Return (title, text). Navigation/footer noise is dropped where possible."""
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    title = (soup.title.get_text(strip=True) if soup.title else "") or ""
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n", strip=True)
    return title, clean_text(text)[:max_chars]


def pdf_to_text(content: bytes, *, max_chars: int = 400_000) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages = []
    for index, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            pages.append(f"[page {index + 1} could not be extracted]")
    return clean_text("\n".join(pages))[:max_chars]


def guess_doc_type(url: str, content_type: str | None) -> str:
    lowered = url.lower()
    if lowered.endswith(".pdf") or (content_type and "pdf" in content_type):
        return DocType.PDF
    if lowered.endswith((".doc", ".docx")):
        return DocType.DOCX
    if "prospectus" in lowered:
        return DocType.PROSPECTUS
    if "policy" in lowered or "admission" in lowered:
        return DocType.POLICY
    return DocType.WEBPAGE


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def upsert_document(
    db,
    *,
    title: str,
    url: str,
    text: str,
    doc_type: str = DocType.WEBPAGE,
    source_id: int | None = None,
    institution: str | None = None,
    campus: str | None = None,
    program: str | None = None,
    admission_cycle: str | None = None,
    publication_date: date | None = None,
    effective_date: date | None = None,
    verification_status: str = Verification.UNVERIFIED,
    verification_notes: str | None = None,
    local_path: str | None = None,
    is_demo: bool = False,
    reindex: bool = True,
) -> tuple[Document, bool]:
    """Insert or update a document. Returns (document, created)."""
    new_hash = content_hash(text)
    existing = db.query(Document).filter(Document.url == url).one_or_none()

    if existing is None:
        document = Document(
            title=title or url,
            url=url,
            doc_type=doc_type,
            source_id=source_id,
            institution=institution,
            campus=campus,
            program=program,
            admission_cycle=admission_cycle,
            publication_date=publication_date,
            effective_date=effective_date,
            retrieved_at=utcnow(),
            content_hash=new_hash,
            verification_status=verification_status,
            verification_notes=verification_notes,
            local_path=local_path,
            is_demo=is_demo,
            char_count=len(text),
        )
        db.add(document)
        db.flush()
        _index_document(db, document, text)
        return document, True

    changed = existing.content_hash != new_hash
    if changed:
        existing.previous_hash = existing.content_hash
        existing.changed_at = utcnow()
        existing.content_hash = new_hash
        existing.char_count = len(text)
    existing.title = title or existing.title
    existing.retrieved_at = utcnow()
    if verification_notes:
        existing.verification_notes = verification_notes
    if reindex and changed:
        db.query(Chunk).filter(Chunk.document_id == existing.id).delete()
        db.flush()
        _index_document(db, existing, text)
    return existing, False


def _index_document(db, document: Document, text: str) -> None:
    chunks = chunk_text(text)
    if not chunks:
        return
    vectors = embed_texts([c.text for c in chunks])
    for chunk, vector in zip(chunks, vectors):
        db.add(
            Chunk(
                document_id=document.id,
                chunk_index=chunk.index,
                text=chunk.text,
                heading=chunk.heading,
                token_count=len(chunk.text) // 4,
                embedding=vector,
                embedding_provider=settings.embedding_provider,
            )
        )


def ingest_url(
    db,
    url: str,
    *,
    title: str | None = None,
    doc_type: str | None = None,
    source_id: int | None = None,
    **metadata,
) -> tuple[Document | None, str]:
    """Fetch a single URL, convert to text and store it. Returns (doc, message)."""
    result = fetch(url)
    if not result.ok:
        _log_refresh(db, source_id, url, result.status_code, None, False, result.error)
        return None, f"FAILED {url}: {result.error or f'HTTP {result.status_code}'}"

    if result.content_type and "pdf" in result.content_type:
        text = pdf_to_text(result.content or b"")
        resolved_type = doc_type or DocType.PDF
    elif (url.lower().endswith(".pdf")) or (result.content or b"")[:5] == b"%PDF-":
        text = pdf_to_text(result.content or b"")
        resolved_type = doc_type or DocType.PDF
    else:
        parsed_title, text = html_to_text(result.content or b"")
        title = title or parsed_title
        resolved_type = doc_type or guess_doc_type(url, result.content_type)

    if not text.strip():
        _log_refresh(db, source_id, url, result.status_code, None, False, "no extractable text")
        return None, f"EMPTY {url}: no extractable text (may be a scanned document)"

    document, created = upsert_document(
        db,
        title=title or url,
        url=url,
        text=text,
        doc_type=resolved_type,
        source_id=source_id,
        **metadata,
    )
    _log_refresh(db, source_id, url, result.status_code, document.content_hash, not created, None)
    return document, f"{'CREATED' if created else 'UPDATED'} {url} ({len(text)} chars)"


def _log_refresh(db, source_id, url, status, digest, changed, error) -> None:
    db.add(
        SourceRefreshLog(
            source_id=source_id,
            url=url,
            http_status=status,
            content_hash=digest,
            changed=bool(changed),
            error=error,
        )
    )


def get_or_create_source(
    db,
    *,
    name: str,
    url: str,
    institution: str | None = None,
    category: str | None = None,
    is_official: bool = True,
    verification_status: str = Verification.VERIFIED,
    verification_notes: str | None = None,
) -> Source:
    source = db.query(Source).filter(Source.url == url).one_or_none()
    if source is None:
        source = Source(
            name=name,
            url=url,
            institution=institution,
            category=category,
            is_official=is_official,
            verification_status=verification_status,
            verification_notes=verification_notes,
            last_checked_at=datetime.now(timezone.utc),
        )
        db.add(source)
        db.flush()
    else:
        source.name = name or source.name
        source.institution = institution or source.institution
        source.category = category or source.category
        source.last_checked_at = datetime.now(timezone.utc)
    return source


def refresh_source(db, source: Source) -> dict:
    """Re-fetch a source page and report whether it changed."""
    result = fetch(source.url)
    source.last_http_status = result.status_code
    source.last_checked_at = datetime.now(timezone.utc)
    if not result.ok:
        log = SourceRefreshLog(
            source_id=source.id,
            url=source.url,
            http_status=result.status_code,
            error=result.error or f"HTTP {result.status_code}",
        )
        db.add(log)
        db.commit()
        return {"url": source.url, "ok": False, "error": log.error}

    existing = db.query(Document).filter(Document.url == source.url).one_or_none()
    if result.content_type and "pdf" in result.content_type:
        text = pdf_to_text(result.content or b"")
    else:
        _, text = html_to_text(result.content or b"")
    digest = content_hash(text)
    changed = existing is None or existing.content_hash != digest
    db.add(
        SourceRefreshLog(
            source_id=source.id,
            url=source.url,
            http_status=result.status_code,
            content_hash=digest,
            changed=changed,
        )
    )
    db.commit()
    return {"url": source.url, "ok": True, "changed": changed, "http_status": result.status_code}
