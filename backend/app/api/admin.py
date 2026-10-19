from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import BASE_DIR
from ..constants import DocType, Role, Verification
from ..db import get_db
from ..models import AuditEntry, Document, Source, SourceRefreshLog, User
from ..schemas import (
    DocumentOut,
    DocumentVerify,
    LoginRequest,
    SourceCreate,
    SourceOut,
    TokenResponse,
    UserOut,
)
from ..security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    require_staff,
)
from ..services.ingest import (
    get_or_create_source,
    html_to_text,
    pdf_to_text,
    refresh_source,
    upsert_document,
)

router = APIRouter(tags=["admin"])

UPLOAD_DIR = BASE_DIR.parent / "data" / "uploads"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_SUFFIXES = {".pdf", ".txt", ".md", ".html", ".htm"}


def _audit(db: Session, actor: str, entity_type: str, entity_id: int | None, action: str, details: dict | None = None) -> None:
    db.add(
        AuditEntry(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            details=details or {},
        )
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    _audit(db, user.email, "user", user.id, "login")
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.email, user.role),
        role=user.role,
        email=user.email,
    )


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db), _: User = Depends(require_staff)) -> dict:
    return {
        "sources": db.query(Source).count(),
        "documents": db.query(Document).count(),
        "unverified_documents": db.query(Document)
        .filter(Document.verification_status == Verification.UNVERIFIED)
        .count(),
        "audit_entries": db.query(AuditEntry).count(),
    }


@router.post("/admin/sources", response_model=SourceOut, status_code=201)
def create_source(
    payload: SourceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> Source:
    existing = db.scalar(select(Source).where(Source.url == payload.url))
    if existing:
        raise HTTPException(status_code=409, detail="A source with this URL already exists.")
    source = get_or_create_source(
        db,
        name=payload.name,
        url=payload.url,
        institution=payload.institution,
        category=payload.category,
        is_official=payload.is_official,
        verification_status=payload.verification_status,
        verification_notes=payload.verification_notes,
    )
    _audit(db, user.email, "source", source.id, "create", {"url": payload.url})
    db.commit()
    db.refresh(source)
    return source


@router.post("/admin/sources/{source_id}/refresh")
def refresh_one(
    source_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
) -> dict:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    result = refresh_source(db, source)
    _audit(db, user.email, "source", source_id, "refresh", result)
    db.commit()
    return result


@router.get("/admin/refresh-logs")
def refresh_logs(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
    _: User = Depends(require_staff),
) -> list[dict]:
    logs = list(
        db.scalars(select(SourceRefreshLog).order_by(SourceRefreshLog.checked_at.desc()).limit(limit)).all()
    )
    return [
        {
            "id": log.id,
            "source_id": log.source_id,
            "url": log.url,
            "http_status": log.http_status,
            "changed": log.changed,
            "error": log.error,
            "checked_at": log.checked_at.isoformat() if log.checked_at else None,
        }
        for log in logs
    ]


@router.post("/admin/documents/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    institution: str | None = Form(default=None),
    doc_type: str | None = Form(default=None),
    admission_cycle: str | None = Form(default=None),
    source_url: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
) -> Document:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix or 'unknown'}'. Allowed: {', '.join(sorted(ALLOWED_SUFFIXES))}.",
        )
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 15 MB upload limit.")
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    if suffix == ".pdf":
        text = pdf_to_text(content)
        resolved_type = doc_type or DocType.PDF
    elif suffix in {".html", ".htm"}:
        _, text = html_to_text(content)
        resolved_type = doc_type or DocType.WEBPAGE
    else:
        text = content.decode("utf-8", errors="ignore")
        resolved_type = doc_type or DocType.WEBPAGE

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No extractable text found. Scanned PDFs need OCR and must be processed manually.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()[:16]
    saved = UPLOAD_DIR / f"{digest}{suffix}"
    saved.write_bytes(content)

    url = source_url or f"upload://{saved.name}"
    source = None
    if source_url:
        source = db.scalar(select(Source).where(Source.url == source_url))

    document, _created = upsert_document(
        db,
        title=title or file.filename or saved.name,
        url=url,
        text=text,
        doc_type=resolved_type,
        source_id=source.id if source else None,
        institution=institution,
        admission_cycle=admission_cycle,
        verification_status=Verification.UNVERIFIED,
        verification_notes=f"Uploaded by {user.email}; awaiting review.",
        local_path=str(saved),
    )
    _audit(db, user.email, "document", document.id, "upload", {"filename": file.filename, "bytes": len(content)})
    db.commit()
    db.refresh(document)
    return document


@router.post("/admin/documents/{document_id}/verify", response_model=DocumentOut)
def verify_document(
    document_id: int,
    payload: DocumentVerify,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    document.verification_status = payload.verification_status
    document.verification_notes = payload.verification_notes or document.verification_notes
    _audit(
        db,
        user.email,
        "document",
        document_id,
        "verify",
        {"status": payload.verification_status},
    )
    db.commit()
    db.refresh(document)
    return document


@router.post("/admin/users", response_model=UserOut, status_code=201)
def create_user(
    email: str = Form(...),
    password: str = Form(..., min_length=10),
    role: str = Form(default=Role.REVIEWER),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> User:
    if role not in {Role.ADMIN, Role.REVIEWER}:
        raise HTTPException(status_code=422, detail="Role must be 'admin' or 'reviewer'.")
    normalized = email.lower().strip()
    if db.scalar(select(User).where(User.email == normalized)):
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    created = User(email=normalized, password_hash=hash_password(password), role=role)
    db.add(created)
    _audit(db, user.email, "user", None, "create", {"email": normalized, "role": role})
    db.commit()
    db.refresh(created)
    return created


@router.get("/admin/audit")
def audit_trail(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
    _: User = Depends(require_staff),
) -> list[dict]:
    entries = list(db.scalars(select(AuditEntry).order_by(AuditEntry.created_at.desc()).limit(limit)).all())
    return [
        {
            "id": e.id,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "action": e.action,
            "actor": e.actor,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]
