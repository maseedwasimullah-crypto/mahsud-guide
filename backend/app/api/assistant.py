from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Conversation, ConversationMessage, User
from ..schemas import ChatRequest, ChatResponse, SearchHit, SearchRequest
from ..security import bearer_scheme, decode_token
from ..services.agent import answer_question, knowledge_base_overview
from ..services.retrieval import search_chunks
from ..utils.time import now_iso_pakistan, pakistan_now, pakistan_today
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

router = APIRouter(tags=["assistant"])

_MAX_HISTORY_TURNS = 12
_MAX_STORED_MESSAGES = 400


@router.get("/assistant/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    return knowledge_base_overview(db)


@router.get("/time")
def current_time() -> dict:
    """Current date/time in Peshawar (Asia/Karachi), computed server-side.

    The client never sends a date; the server clock is the single source of
    truth so relative questions ("today", "this week") resolve consistently.
    """
    now = pakistan_now()
    return {
        "timezone": "Asia/Karachi",
        "timezone_label": "Pakistan Standard Time (Asia/Karachi)",
        "date": now.date().isoformat(),
        "date_display": now.strftime("%A, %d %B %Y"),
        "time": now.strftime("%H:%M:%S"),
        "iso": now_iso_pakistan(),
        "utc_offset": now.strftime("%z"),
        "day_of_week": now.strftime("%A"),
        "today": pakistan_today(),
    }


def _optional_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        email = payload.get("sub")
        if not email:
            return None
        return db.scalar(select(User).where(User.email == email))
    except Exception:  # noqa: BLE001
        return None


def _load_context_messages(
    db: Session,
    conversation: Conversation | None,
    inline_history: list[dict] | None,
) -> list[dict]:
    """Return prior turns as [{'role','content'}] for follow-up context.

    Only the last ``_MAX_HISTORY_TURNS`` exchanges are used to bound tokens.
    """
    if conversation is not None:
        prior = list(conversation.messages[-_MAX_HISTORY_TURNS:])
        return [{"role": m.role, "content": m.content} for m in prior]
    if inline_history:
        cleaned = [
            {"role": m.get("role", "user"), "content": str(m.get("content", ""))[:4000]}
            for m in inline_history
            if m.get("role") in {"user", "assistant"} and m.get("content")
        ]
        return cleaned[-_MAX_HISTORY_TURNS:]
    return []


def _attach_conversation(
    db: Session,
    conversation_id: int | None,
    guest_id: str | None,
    user: User | None,
) -> Conversation | None:
    if conversation_id is None:
        return None
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if user is not None:
        allowed = conversation.user_id == user.id
    else:
        allowed = conversation.user_id is None and bool(guest_id) and conversation.guest_id == guest_id
    if not allowed:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@router.post("/assistant/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    return _run_chat(db, payload, conversation=None, history=None)


def _run_chat(
    db: Session,
    payload: ChatRequest,
    *,
    conversation: Conversation | None,
    history: list[dict] | None,
) -> ChatResponse:
    profile = {
        "hssc_percent": payload.hssc_percent,
        "mdcat_percent": payload.mdcat_percent,
        "entrance_test_percent": payload.entrance_test_percent,
        "subjects": payload.subjects,
    }
    context = _load_context_messages(db, conversation, history)
    answer = answer_question(
        db,
        payload.message,
        program=payload.program,
        profile=profile,
        formula_id=payload.formula_id,
        aggregate_inputs=payload.aggregate_inputs,
        history=context,
    )
    response = ChatResponse(**answer.as_dict())
    if conversation is not None:
        _persist_turn(db, conversation, payload.message, response)
    return response


def _persist_turn(
    db: Session,
    conversation: Conversation,
    user_message: str,
    response: ChatResponse,
) -> None:
    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=user_message,
        )
    )
    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=response.answer,
            intent=response.intent,
            citations=[c for c in response.citations],
            disclaimers=response.disclaimers,
            missing_information=response.missing_information,
            provider_configured=response.provider_configured,
            generated_by=response.generated_by,
        )
    )
    conversation.last_message_at = pakistan_now()
    if conversation.title == "New conversation" and user_message.strip():
        conversation.title = user_message.strip()[:120]
    # Guard against unbounded growth of a single thread.
    total = len(conversation.messages)
    if total > _MAX_STORED_MESSAGES:
        overflow = conversation.messages[: total - _MAX_STORED_MESSAGES]
        for m in overflow:
            db.delete(m)
    db.commit()


@router.post("/assistant/chat/conversation", response_model=ChatResponse)
def chat_with_conversation(
    payload: dict,
    db: Session = Depends(get_db),
    user: User | None = Depends(_optional_authenticated_user),
) -> ChatResponse:
    """Chat endpoint that persists turns into a stored conversation.

    Accepts the normal ChatRequest fields plus ``conversation_id``,
    ``guest_id`` and optional ``history`` for stateless follow-ups.
    """
    try:
        request = ChatRequest(
            message=payload["message"],
            program=payload.get("program"),
            hssc_percent=payload.get("hssc_percent"),
            mdcat_percent=payload.get("mdcat_percent"),
            entrance_test_percent=payload.get("entrance_test_percent"),
            subjects=payload.get("subjects"),
            formula_id=payload.get("formula_id"),
            aggregate_inputs=payload.get("aggregate_inputs"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid chat payload: {exc}") from exc

    conversation = _attach_conversation(
        db, payload.get("conversation_id"), payload.get("guest_id"), user
    )
    history = payload.get("history")
    return _run_chat(db, request, conversation=conversation, history=history)


@router.post("/search", response_model=list[SearchHit])
def search(payload: SearchRequest, db: Session = Depends(get_db)) -> list[SearchHit]:
    hits = search_chunks(
        db,
        payload.query,
        limit=payload.limit,
        doc_types=payload.doc_types,
        institution=payload.institution,
        admission_cycle=payload.admission_cycle,
        verified_only=payload.verified_only,
    )
    return [
        SearchHit(
            document_id=h.document_id,
            chunk_id=h.chunk_id,
            title=h.document_title,
            url=h.document_url,
            institution=h.institution,
            doc_type=h.doc_type,
            publication_date=h.publication_date,
            verification_status=h.verification_status,
            is_demo=h.is_demo,
            score=round(h.score, 5),
            keyword_score=round(h.keyword_score, 5),
            semantic_score=round(h.semantic_score, 5),
            excerpt=h.text[:600],
        )
        for h in hits
    ]
