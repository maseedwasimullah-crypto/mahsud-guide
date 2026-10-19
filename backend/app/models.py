"""Relational data model for MAHSUDo-guide.

Every institutional fact carries provenance: which source it came from, when it
was retrieved, and how far it has been verified. Nothing is marked "official"
unless a human or the ingestion pipeline recorded an official URL for it.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .constants import FormulaStatus, Verification
from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #
class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    institution: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(100))
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)
    verification_notes: Mapped[str | None] = mapped_column(Text)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_http_status: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    documents: Mapped[list[Document]] = relationship(back_populates="source")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), default="webpage")
    institution: Mapped[str | None] = mapped_column(String(200))
    campus: Mapped[str | None] = mapped_column(String(200))
    program: Mapped[str | None] = mapped_column(String(200))
    admission_cycle: Mapped[str | None] = mapped_column(String(100))
    publication_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)
    verification_notes: Mapped[str | None] = mapped_column(Text)
    local_path: Mapped[str | None] = mapped_column(String(500))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0)

    source: Mapped[Source | None] = relationship(back_populates="documents")
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_documents_status", "verification_status"),)


class Chunk(Base):
    """A retrieval unit. Text plus a serialised embedding vector."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(300))
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list | None] = mapped_column(JSON)
    embedding_provider: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_index"),
    )


class SourceRefreshLog(Base):
    """Change-detection history for scheduled/manual source refreshes."""

    __tablename__ = "source_refresh_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(1000))
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    changed: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --------------------------------------------------------------------------- #
# Institutions
# --------------------------------------------------------------------------- #
class Institution(Base, TimestampMixin):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(400), nullable=False, index=True)
    short_name: Mapped[str | None] = mapped_column(String(80))
    institution_type: Mapped[str] = mapped_column(String(50), default="other")
    city: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)
    verification_notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("name", "institution_type", name="uq_institution_name_type"),
        Index("ix_institutions_type", "institution_type"),
    )


class Campus(Base, TimestampMixin):
    __tablename__ = "campuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL")
    )
    city: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL")
    )
    source_url: Mapped[str | None] = mapped_column(String(1000))
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)


# --------------------------------------------------------------------------- #
# Academics
# --------------------------------------------------------------------------- #
class Program(Base, TimestampMixin):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(400), nullable=False, index=True)
    short_name: Mapped[str | None] = mapped_column(String(80))
    degree_level: Mapped[str] = mapped_column(String(50), default="undergraduate", index=True)
    discipline: Mapped[str | None] = mapped_column(String(150))
    duration_years: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)

    offerings: Mapped[list[ProgramOffering]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("title", "degree_level", name="uq_program_title_level"),)


class ProgramOffering(Base, TimestampMixin):
    """Links a program to the institution(s) that offer it."""

    __tablename__ = "program_offerings"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"))
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL")
    )
    institution_name: Mapped[str | None] = mapped_column(String(400))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)

    program: Mapped[Program] = relationship(back_populates="offerings")


class CurriculumRecord(Base, TimestampMixin):
    __tablename__ = "curriculum_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int | None] = mapped_column(ForeignKey("programs.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    session: Mapped[str | None] = mapped_column(String(100))
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    source_url: Mapped[str | None] = mapped_column(String(1000))
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)


class FacultyMember(Base, TimestampMixin):
    __tablename__ = "faculty_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(300))
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL")
    )
    source_url: Mapped[str | None] = mapped_column(String(1000))
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)


class Policy(Base, TimestampMixin):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120))
    summary: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    source_url: Mapped[str | None] = mapped_column(String(1000))
    effective_date: Mapped[date | None] = mapped_column(Date)
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)


# --------------------------------------------------------------------------- #
# Admissions
# --------------------------------------------------------------------------- #
class AdmissionCycle(Base, TimestampMixin):
    __tablename__ = "admission_cycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    session: Mapped[str] = mapped_column(String(50), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(200))
    portal_url: Mapped[str | None] = mapped_column(String(1000))
    form_open_date: Mapped[date | None] = mapped_column(Date)
    form_close_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="active")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)

    __table_args__ = (UniqueConstraint("name", "session", name="uq_cycle_name_session"),)


class AdmissionRule(Base, TimestampMixin):
    __tablename__ = "admission_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int | None] = mapped_column(
        ForeignKey("admission_cycles.id", ondelete="SET NULL")
    )
    program_id: Mapped[int | None] = mapped_column(ForeignKey("programs.id", ondelete="SET NULL"))
    program_scope: Mapped[str | None] = mapped_column(String(200))
    rule_type: Mapped[str] = mapped_column(String(50), default="eligibility")
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    min_hssc_percent: Mapped[float | None] = mapped_column(Float)
    min_mdcat_percent: Mapped[float | None] = mapped_column(Float)
    min_entrance_percent: Mapped[float | None] = mapped_column(Float)
    required_subjects: Mapped[list | None] = mapped_column(JSON)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    source_url: Mapped[str | None] = mapped_column(String(1000))
    effective_date: Mapped[date | None] = mapped_column(Date)
    verification_status: Mapped[str] = mapped_column(String(30), default=Verification.UNVERIFIED)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("ix_rules_type", "rule_type"),)


class AggregateFormula(Base, TimestampMixin):
    """A weighted-merit formula.

    ``components`` is a list of dicts:
        {"key": "ssc", "label": "SSC / Matric", "weight": 0.10,
         "input": "percent" | "marks", "max_marks": 1100, "min_marks": 0}
    Weights must sum to 1.0. Only ``status == active`` formulas are exposed to
    the calculator, and only when ``verified`` is true.
    """

    __tablename__ = "aggregate_formulas"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    program_scope: Mapped[str] = mapped_column(String(300), nullable=False)
    admission_session: Mapped[str] = mapped_column(String(50), nullable=False)
    cycle_id: Mapped[int | None] = mapped_column(
        ForeignKey("admission_cycles.id", ondelete="SET NULL")
    )
    components: Mapped[list] = mapped_column(JSON, nullable=False)
    rounding: Mapped[int] = mapped_column(Integer, default=5)
    explanation: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    source_title: Mapped[str | None] = mapped_column(String(500))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default=FormulaStatus.PENDING)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    verification_notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("name", "admission_session", name="uq_formula_name_session"),
    )


# --------------------------------------------------------------------------- #
# Operations
# --------------------------------------------------------------------------- #
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    full_name: Mapped[str | None] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="reviewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditEntry(Base):
    __tablename__ = "audit_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(80))
    actor: Mapped[str | None] = mapped_column(String(200))
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)


# --------------------------------------------------------------------------- #
# Conversations (chat history)
# --------------------------------------------------------------------------- #
class Conversation(Base, TimestampMixin):
    """A chat thread. Owned by a user when authenticated, or by an anonymous
    guest id (a random UUID stored client-side) so conversations remain private."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    guest_id: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(300), default="New conversation")
    session_key: Mapped[str | None] = mapped_column(String(64))  # reserved
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list[ConversationMessage]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.id"
    )

    __table_args__ = (
        Index("ix_conversations_user", "user_id"),
        Index("ix_conversations_guest", "guest_id"),
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(50))
    citations: Mapped[list | None] = mapped_column(JSON)
    disclaimers: Mapped[list | None] = mapped_column(JSON)
    missing_information: Mapped[list | None] = mapped_column(JSON)
    provider_configured: Mapped[bool | None] = mapped_column(Boolean)
    generated_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
