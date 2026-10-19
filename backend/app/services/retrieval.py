"""Hybrid retrieval over ingested official documents.

Semantic (embedding cosine) and lexical (BM25-style) scores are combined so the
system still returns useful evidence when an external embedding provider is not
configured. Every result carries its provenance for citation.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import Verification
from ..models import Chunk, Document, Source
from .embeddings import cosine, embed_query

TOKEN_RE = re.compile(r"[a-z0-9]+")
K1 = 1.5
B = 0.75

# Minimum blended relevance for a chunk to be presented as evidence. Results
# below this floor are unrelated noise (measured: unrelated queries score
# <=0.03, genuine keyword matches >=0.4 with this corpus). Dropping them lets
# the agent say "not found" honestly instead of quoting a random document.
MIN_EVIDENCE_SCORE = 0.1


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    text: str
    heading: str | None
    document_title: str
    document_url: str
    doc_type: str | None
    institution: str | None
    program: str | None
    admission_cycle: str | None
    publication_date: str | None
    retrieved_at: str | None
    verification_status: str
    is_demo: bool
    source_name: str | None
    score: float = 0.0
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    flags: list[str] = field(default_factory=list)

    @property
    def citation(self) -> dict:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "title": self.document_title,
            "url": self.document_url,
            "institution": self.institution,
            "doc_type": self.doc_type,
            "publication_date": self.publication_date,
            "retrieved_at": self.retrieved_at,
            "verification_status": self.verification_status,
            "is_demo": self.is_demo,
            "source_name": self.source_name,
        }


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def _bm25(query_terms: list[str], doc_terms: list[str], avg_len: float, df: dict[str, int], n_docs: int) -> float:
    if not doc_terms:
        return 0.0
    dl = len(doc_terms)
    tf: dict[str, int] = {}
    for token in doc_terms:
        tf[token] = tf.get(token, 0) + 1
    score = 0.0
    for term in set(query_terms):
        if term not in tf:
            continue
        idf = math.log(1 + (n_docs - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
        numerator = tf[term] * (K1 + 1)
        denominator = tf[term] + K1 * (1 - B + B * dl / max(avg_len, 1e-9))
        score += idf * numerator / denominator
    return score


def search_chunks(
    db: Session,
    query: str,
    *,
    limit: int = 6,
    doc_types: list[str] | None = None,
    institution: str | None = None,
    program: str | None = None,
    admission_cycle: str | None = None,
    verified_only: bool = False,
    include_demo: bool = True,
) -> list[RetrievedChunk]:
    stmt = (
        select(Chunk, Document, Source)
        .join(Document, Chunk.document_id == Document.id)
        .outerjoin(Source, Document.source_id == Source.id)
    )
    if doc_types:
        stmt = stmt.where(Document.doc_type.in_(doc_types))
    if institution:
        stmt = stmt.where(Document.institution.ilike(f"%{institution}%"))
    if program:
        stmt = stmt.where(Document.program.ilike(f"%{program}%"))
    if admission_cycle:
        stmt = stmt.where(Document.admission_cycle.ilike(f"%{admission_cycle}%"))
    if verified_only:
        stmt = stmt.where(Document.verification_status != Verification.UNVERIFIED)
    if not include_demo:
        stmt = stmt.where(Document.is_demo.is_(False))

    rows = db.execute(stmt).all()
    if not rows:
        return []

    query_terms = _tokens(query)
    corpus_terms: list[list[str]] = []
    df: dict[str, int] = {}
    for chunk, _doc, _src in rows:
        terms = _tokens(chunk.text)
        corpus_terms.append(terms)
        for term in set(terms):
            df[term] = df.get(term, 0) + 1
    avg_len = sum(len(t) for t in corpus_terms) / max(len(corpus_terms), 1)
    n_docs = len(rows)

    query_vec, provider = embed_query(query)

    results: list[RetrievedChunk] = []
    for (chunk, doc, src), terms in zip(rows, corpus_terms):
        kw = _bm25(query_terms, terms, avg_len, df, n_docs)
        sem = 0.0
        if chunk.embedding and chunk.embedding_provider == provider:
            sem = max(0.0, cosine(query_vec, chunk.embedding))
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=doc.id,
                text=chunk.text,
                heading=chunk.heading,
                document_title=doc.title,
                document_url=doc.url,
                doc_type=doc.doc_type,
                institution=doc.institution,
                program=doc.program,
                admission_cycle=doc.admission_cycle,
                publication_date=doc.publication_date.isoformat() if doc.publication_date else None,
                retrieved_at=doc.retrieved_at.isoformat() if doc.retrieved_at else None,
                verification_status=doc.verification_status,
                is_demo=bool(doc.is_demo),
                source_name=src.name if src else None,
                keyword_score=kw,
                semantic_score=sem,
            )
        )

    max_kw = max((r.keyword_score for r in results), default=0.0) or 1.0
    semantic_available = any(r.semantic_score > 0 for r in results)
    for item in results:
        kw_norm = item.keyword_score / max_kw
        if semantic_available:
            item.score = 0.6 * item.semantic_score + 0.4 * kw_norm
        else:
            item.score = kw_norm
        if item.is_demo:
            item.flags.append("demo_record")
        if item.verification_status == Verification.CONFLICTING:
            item.flags.append("conflicting_sources")
        if item.verification_status == Verification.HISTORICAL:
            item.flags.append("historical")

    results.sort(key=lambda r: r.score, reverse=True)
    # Discard results below the relevance floor (they are unrelated noise).
    results = [r for r in results if r.score >= MIN_EVIDENCE_SCORE]
    return results[:limit]


def document_catalog(db: Session, *, limit: int = 200, doc_type: str | None = None) -> list[Document]:
    stmt = select(Document).order_by(Document.retrieved_at.desc())
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    return list(db.scalars(stmt.limit(limit)).all())
