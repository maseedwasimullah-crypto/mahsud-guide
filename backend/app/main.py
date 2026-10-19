"""FastAPI application entry point."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from .config import settings
from .constants import Verification
from .db import SessionLocal, init_db
from .rate_limit import limiter
from .services.llm import llm_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("mahsud")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info("MAHSUDo-guide API starting (environment=%s)", settings.environment)
    status = llm_status()
    if not status.configured:
        logger.info("AI provider not configured: %s", status.detail)
    yield
    logger.info("MAHSUDo-guide API shutting down")


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=(
        "Source-aware university guidance API for Khyber Medical University. "
        "Read-only official-source search, deterministic aggregate calculation and rule-based "
        "eligibility checks. Independent project; not an official KMU service."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def rate_limit_and_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    if request.method != "OPTIONS" and not request.url.path.startswith(("/docs", "/openapi.json")):
        client = request.client.host if request.client else "unknown"
        allowed, retry_after = limiter.check(client)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down and try again shortly.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    # Never log query strings or bodies: they can contain student details.
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Request validation failed.", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_handler(_request: Request, exc: Exception):  # pragma: no cover
    logger.exception("unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )


@app.get("/api/health")
def health() -> dict:
    from .models import Chunk, Document, Institution, Program, Source

    status = llm_status()
    db_status = "ok"
    counts: dict[str, int] = {}
    try:
        db = SessionLocal()
        try:
            counts = {
                "sources": db.scalar(select(func.count(Source.id))) or 0,
                "documents": db.scalar(select(func.count(Document.id))) or 0,
                "chunks": db.scalar(select(func.count(Chunk.id))) or 0,
                "programs": db.scalar(select(func.count(Program.id))) or 0,
                "institutions": db.scalar(select(func.count(Institution.id))) or 0,
                "unverified_documents": db.scalar(
                    select(func.count(Document.id)).where(
                        Document.verification_status == Verification.UNVERIFIED
                    )
                )
                or 0,
            }
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {type(exc).__name__}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "environment": settings.environment,
        "database": db_status,
        "llm_provider": status.provider,
        "llm_configured": status.configured,
        "llm_detail": status.detail,
        "embedding_provider": settings.embedding_provider,
        "counts": counts,
    }


def _include_routers() -> None:
    from .api import admin, admissions, assistant, conversations, catalog

    app.include_router(catalog.router, prefix="/api")
    app.include_router(admissions.router, prefix="/api")
    app.include_router(assistant.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")


_include_routers()
