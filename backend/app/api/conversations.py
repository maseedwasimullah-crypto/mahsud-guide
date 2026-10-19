"""Conversation (chat history) endpoints.

Ownership model:
* Authenticated conversations belong to ``user_id`` and are only visible to
  that user (enforced with a 404 when someone else's id is supplied).
* Guest conversations belong to a random ``guest_id`` generated client-side
  and stored in the browser; the server never sees a login for them. Knowing
  the guest id grants access, so the frontend must keep it private.

Nothing here ever stores student personal data: messages contain only the
text of the conversation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Conversation, ConversationMessage, User
from ..schemas import ConversationCreate, ConversationDetail, ConversationOut, MessageOut
from ..security import get_current_user, bearer_scheme
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _message_count(db: Session, conversation_id: int) -> int:
    return (
        db.scalar(
            select(func.count(ConversationMessage.id)).where(
                ConversationMessage.conversation_id == conversation_id
            )
        )
        or 0
    )


def _can_access(conversation: Conversation, user: User | None, guest_id: str | None) -> bool:
    if user is not None:
        return conversation.user_id == user.id
    if guest_id and conversation.guest_id == guest_id:
        return True
    return False


def _optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        from ..security import decode_token

        payload = decode_token(credentials.credentials)
        email = payload.get("sub")
        if not email:
            return None
        return db.scalar(select(User).where(User.email == email))
    except Exception:  # noqa: BLE001
        return None


def _to_out(db: Session, conversation: Conversation) -> ConversationOut:
    out = ConversationOut.model_validate(conversation)
    out.message_count = _message_count(db, conversation.id)
    return out


@router.post("", response_model=ConversationOut, status_code=201)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(_optional_user),
) -> ConversationOut:
    if user is None and not payload.guest_id:
        raise HTTPException(
            status_code=400,
            detail="Provide a guest_id for anonymous conversations or log in.",
        )
    conversation = Conversation(
        user_id=user.id if user else None,
        guest_id=None if user else payload.guest_id,
        title=(payload.title or "New conversation")[:300],
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return _to_out(db, conversation)


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    user: User | None = Depends(_optional_user),
    guest_id: str | None = None,
    limit: int = 50,
) -> list[ConversationOut]:
    stmt = select(Conversation)
    if user is not None:
        stmt = stmt.where(Conversation.user_id == user.id)
    elif guest_id:
        stmt = stmt.where(Conversation.guest_id == guest_id, Conversation.user_id.is_(None))
    else:
        return []
    stmt = stmt.order_by(
        func.coalesce(Conversation.last_message_at, Conversation.updated_at).desc()
    ).limit(min(limit, 200))
    return [_to_out(db, c) for c in db.scalars(stmt).all()]


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(_optional_user),
    guest_id: str | None = None,
) -> ConversationDetail:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or not _can_access(conversation, user, guest_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    detail = ConversationDetail.model_validate(conversation)
    detail.message_count = len(conversation.messages)
    detail.messages = [MessageOut.model_validate(m) for m in conversation.messages]
    return detail


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(_optional_user),
    guest_id: str | None = None,
) -> dict:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or not _can_access(conversation, user, guest_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    db.delete(conversation)
    db.commit()
    return {"deleted": True}
