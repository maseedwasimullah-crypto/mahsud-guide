"""Pydantic request/response schemas (validated at the API boundary)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Sources & documents
# --------------------------------------------------------------------------- #
class SourceOut(ORMModel):
    id: int
    name: str
    url: str
    institution: str | None
    category: str | None
    is_official: bool
    verification_status: str
    verification_notes: str | None
    last_checked_at: datetime | None
    last_http_status: int | None
    notes: str | None


class SourceCreate(BaseModel):
    name: str = Field(min_length=3, max_length=300)
    url: str = Field(min_length=8, max_length=1000)
    institution: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    is_official: bool = True
    verification_status: Literal["verified", "unverified", "conflicting", "historical", "demo"] = "unverified"
    verification_notes: str | None = None

    @field_validator("url")
    @classmethod
    def _url_scheme(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return value


class DocumentOut(ORMModel):
    id: int
    title: str
    url: str
    doc_type: str
    institution: str | None
    campus: str | None
    program: str | None
    admission_cycle: str | None
    publication_date: date | None
    effective_date: date | None
    retrieved_at: datetime
    content_hash: str | None
    changed_at: datetime | None
    verification_status: str
    verification_notes: str | None
    is_demo: bool
    char_count: int


class DocumentDetail(DocumentOut):
    chunk_count: int = 0
    preview: list[dict] = Field(default_factory=list)


class DocumentVerify(BaseModel):
    verification_status: Literal["verified", "unverified", "conflicting", "historical", "demo"]
    verification_notes: str | None = None


# --------------------------------------------------------------------------- #
# Institutions / programs
# --------------------------------------------------------------------------- #
class InstitutionOut(ORMModel):
    id: int
    name: str
    short_name: str | None
    institution_type: str
    city: str | None
    address: str | None
    phone: str | None
    email: str | None
    website: str | None
    source_url: str | None
    verification_status: str
    verification_notes: str | None


class CampusOut(ORMModel):
    id: int
    name: str
    city: str | None
    address: str | None
    phone: str | None
    website: str | None
    source_url: str | None
    verification_status: str


class ProgramOut(ORMModel):
    id: int
    title: str
    short_name: str | None
    degree_level: str
    discipline: str | None
    duration_years: float | None
    description: str | None
    source_url: str | None
    verification_status: str


class ProgramDetail(ProgramOut):
    offerings: list[dict] = Field(default_factory=list)


class ProgramListResponse(BaseModel):
    total: int
    items: list[ProgramOut]


class InstitutionListResponse(BaseModel):
    total: int
    items: list[InstitutionOut]


class FacultyOut(ORMModel):
    id: int
    name: str
    designation: str | None
    department: str | None
    source_url: str | None
    verification_status: str


class CurriculumOut(ORMModel):
    id: int
    title: str
    session: str | None
    source_url: str | None
    verification_status: str


class PolicyOut(ORMModel):
    id: int
    title: str
    category: str | None
    summary: str | None
    source_url: str | None
    effective_date: date | None
    verification_status: str


# --------------------------------------------------------------------------- #
# Admissions
# --------------------------------------------------------------------------- #
class AdmissionCycleOut(ORMModel):
    id: int
    name: str
    session: str
    institution: str | None
    portal_url: str | None
    form_open_date: date | None
    form_close_date: date | None
    status: str
    source_url: str | None
    verification_status: str


class AdmissionRuleOut(ORMModel):
    id: int
    program_scope: str | None
    rule_type: str
    title: str
    text: str
    min_hssc_percent: float | None
    min_mdcat_percent: float | None
    min_entrance_percent: float | None
    required_subjects: list | None
    source_url: str | None
    effective_date: date | None
    verification_status: str
    is_demo: bool


class FormulaOut(BaseModel):
    id: int
    name: str
    program_scope: str
    admission_session: str
    components: list[dict]
    rounding: int
    verified: bool
    status: str
    source_url: str | None
    source_title: str | None
    effective_from: date | None
    effective_to: date | None
    verification_notes: str | None
    explanation: str | None
    usable: bool


class AggregateRequest(BaseModel):
    formula_id: int
    inputs: dict[str, Any] = Field(default_factory=dict)


class AggregateResponse(BaseModel):
    aggregate: float
    is_estimate: bool
    components: list[dict]
    formula_id: int
    formula_name: str
    program_scope: str
    admission_session: str
    source: dict
    rounding: int
    explanation: str | None
    limitations: list[str]


class EligibilityRequest(BaseModel):
    program: str | None = Field(default=None, max_length=200)
    hssc_percent: float | None = Field(default=None, ge=0, le=100)
    mdcat_percent: float | None = Field(default=None, ge=0, le=100)
    entrance_test_percent: float | None = Field(default=None, ge=0, le=100)
    subjects: list[str] | None = None


class EligibilityResponse(BaseModel):
    status: str
    program: str | None
    evaluations: list[dict]
    missing_information: list[str]
    notes: list[str]
    is_admission_decision: bool


# --------------------------------------------------------------------------- #
# Chat
# --------------------------------------------------------------------------- #
class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    program: str | None = Field(default=None, max_length=200)
    hssc_percent: float | None = Field(default=None, ge=0, le=100)
    mdcat_percent: float | None = Field(default=None, ge=0, le=100)
    entrance_test_percent: float | None = Field(default=None, ge=0, le=100)
    subjects: list[str] | None = None
    formula_id: int | None = None
    aggregate_inputs: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    citations: list[dict]
    evidence: list[dict]
    tools_used: list[dict]
    missing_information: list[str]
    disclaimers: list[str]
    generated_by: str
    provider_configured: bool
    blocked_prompt_injection: list[str]


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=6, ge=1, le=25)
    doc_types: list[str] | None = None
    institution: str | None = None
    admission_cycle: str | None = None
    verified_only: bool = False


class SearchHit(BaseModel):
    document_id: int
    chunk_id: int
    title: str
    url: str
    institution: str | None
    doc_type: str | None
    publication_date: str | None
    verification_status: str
    is_demo: bool
    score: float
    keyword_score: float
    semantic_score: float
    excerpt: str


# --------------------------------------------------------------------------- #
# Auth & admin
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str | None
    role: str
    is_active: bool


class HealthResponse(BaseModel):
    status: str
    environment: str
    database: str
    llm_provider: str
    llm_configured: bool
    embedding_provider: str
    counts: dict


# --------------------------------------------------------------------------- #
# Conversations
# --------------------------------------------------------------------------- #
class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    guest_id: str | None = Field(default=None, max_length=64)


class MessageOut(ORMModel):
    id: int
    role: str
    content: str
    intent: str | None
    citations: list | None
    disclaimers: list | None
    missing_information: list | None
    provider_configured: bool | None
    generated_by: str | None
    created_at: datetime


class ConversationOut(ORMModel):
    id: int
    title: str
    guest_id: str | None
    user_id: int | None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    message_count: int = 0


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ChatWithHistoryRequest(ChatRequest):
    """Chat request that optionally attaches to a stored conversation."""

    conversation_id: int | None = None
    guest_id: str | None = Field(default=None, max_length=64)
    history: list[dict] | None = None  # [{role, content}, ...] for stateless follow-ups
