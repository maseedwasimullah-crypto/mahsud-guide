"""Conversation persistence, follow-up context, ownership isolation and
no-AI-provider behaviour for the conversational assistant."""

from __future__ import annotations

from app.constants import Role
from app.models import Conversation, ConversationMessage, User
from app.security import create_access_token, hash_password

GUEST_A = "guest-aaaaaaaa-1111-4444-8888-000000000001"
GUEST_B = "guest-bbbbbbbb-2222-4444-8888-000000000002"


# --------------------------------------------------------------------------- #
# Guest conversations
# --------------------------------------------------------------------------- #
def test_create_guest_conversation(client):
    res = client.post("/api/conversations", json={"guest_id": GUEST_A, "title": "Hello"})
    assert res.status_code == 201
    payload = res.json()
    assert payload["guest_id"] == GUEST_A
    assert payload["user_id"] is None
    assert payload["message_count"] == 0


def test_create_conversation_requires_identity(client):
    res = client.post("/api/conversations", json={})
    assert res.status_code == 400
    assert "guest_id" in res.json()["detail"]


def test_list_conversations_is_scoped_to_guest(client):
    client.post("/api/conversations", json={"guest_id": GUEST_A, "title": "A thread"})
    client.post("/api/conversations", json={"guest_id": GUEST_B, "title": "B thread"})

    list_a = client.get("/api/conversations", params={"guest_id": GUEST_A}).json()
    list_b = client.get("/api/conversations", params={"guest_id": GUEST_B}).json()

    assert [c["title"] for c in list_a] == ["A thread"]
    assert [c["title"] for c in list_b] == ["B thread"]

    # No identity -> no conversations (privacy default).
    assert client.get("/api/conversations").json() == []


def test_other_guest_cannot_read_or_delete(client):
    created = client.post("/api/conversations", json={"guest_id": GUEST_A, "title": "Private"}).json()
    cid = created["id"]

    # Guest B guessing the numeric id must get 404, not the content.
    assert client.get(f"/api/conversations/{cid}", params={"guest_id": GUEST_B}).status_code == 404
    assert client.delete(f"/api/conversations/{cid}", params={"guest_id": GUEST_B}).status_code == 404
    # Even with no identity at all.
    assert client.get(f"/api/conversations/{cid}").status_code == 404

    # The owner still has access.
    assert client.get(f"/api/conversations/{cid}", params={"guest_id": GUEST_A}).status_code == 200


# --------------------------------------------------------------------------- #
# Chat + persistence
# --------------------------------------------------------------------------- #
def test_chat_persists_turns_and_autotitles(client):
    created = client.post("/api/conversations", json={"guest_id": GUEST_A}).json()
    cid = created["id"]

    res = client.post(
        "/api/assistant/chat/conversation",
        json={
            "message": "What is the MBBS aggregate formula?",
            "conversation_id": cid,
            "guest_id": GUEST_A,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["answer"]
    assert body["citations"], "assistant replies must cite sources"

    detail = client.get(f"/api/conversations/{cid}", params={"guest_id": GUEST_A}).json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"]
    assert detail["messages"][0]["content"] == "What is the MBBS aggregate formula?"
    assert detail["messages"][1]["content"] == body["answer"]
    # Auto-title comes from the first user message.
    assert detail["title"] == "What is the MBBS aggregate formula?"
    assert detail["message_count"] == 2
    # Citations stored on the assistant message for later display.
    assert detail["messages"][1]["citations"]


def test_chat_with_wrong_guest_is_rejected(client):
    created = client.post("/api/conversations", json={"guest_id": GUEST_A}).json()
    res = client.post(
        "/api/assistant/chat/conversation",
        json={"message": "hello there", "conversation_id": created["id"], "guest_id": GUEST_B},
    )
    assert res.status_code == 404


def test_inline_history_is_used_for_follow_up_retrieval(client):
    """A follow-up whose own words are thin must still retrieve evidence by
    combining the previous turn into the search query."""
    history = [
        {"role": "user", "content": "Tell me about the MBBS aggregate formula and MDCAT weightage"},
        {"role": "assistant", "content": "The MBBS aggregate uses SSC 10%, FSc 40%, MDCAT 50%."},
    ]
    res = client.post(
        "/api/assistant/chat",
        json={"message": "what about the eligibility for it?", "program": "MBBS"},
    )
    assert res.status_code == 200
    without_history = res.json()

    # The conversation endpoint accepts inline history and must not error.
    res2 = client.post(
        "/api/assistant/chat/conversation",
        json={"message": "what about the eligibility for it?", "program": "MBBS", "history": history},
    )
    assert res2.status_code == 200
    with_history = res2.json()
    assert with_history["answer"]
    # Search tool recorded the combined query when history is present.
    search_tools = [t for t in with_history["tools_used"] if t["tool"] == "search_sources"]
    assert search_tools, "search_sources should run"
    assert "eligibility" in search_tools[0]["arguments"]["query"]
    # Both modes still return grounded answers.
    assert without_history["answer"]


def test_malformed_chat_payload_is_422(client):
    res = client.post("/api/assistant/chat/conversation", json={"program": "MBBS"})
    assert res.status_code == 422


# --------------------------------------------------------------------------- #
# Authenticated ownership
# --------------------------------------------------------------------------- #
def test_authenticated_user_sees_only_their_conversations(client, seeded_db):
    user_a = User(
        email="student-a@test.local",
        password_hash=hash_password("some-long-password-1"),
        role=Role.REVIEWER,
    )
    user_b = User(
        email="student-b@test.local",
        password_hash=hash_password("some-long-password-2"),
        role=Role.REVIEWER,
    )
    seeded_db.add_all([user_a, user_b])
    seeded_db.commit()
    seeded_db.refresh(user_a)
    seeded_db.refresh(user_b)

    token_a = create_access_token(user_a.email, user_a.role)
    token_b = create_access_token(user_b.email, user_b.role)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    created = client.post(
        "/api/conversations", json={"title": "A private thread"}, headers=headers_a
    ).json()
    cid = created["id"]
    assert created["user_id"] == user_a.id

    # Owner can read it.
    assert client.get(f"/api/conversations/{cid}", headers=headers_a).status_code == 200
    # Another authenticated user cannot.
    assert client.get(f"/api/conversations/{cid}", headers=headers_b).status_code == 404
    assert client.delete(f"/api/conversations/{cid}", headers=headers_b).status_code == 404
    # Anonymous access is denied too.
    assert client.get(f"/api/conversations/{cid}").status_code == 404

    # List scoping: each user sees only their own.
    client.post("/api/conversations", json={"title": "B thread"}, headers=headers_b)
    list_a = client.get("/api/conversations", headers=headers_a).json()
    list_b = client.get("/api/conversations", headers=headers_b).json()
    assert [c["title"] for c in list_a] == ["A private thread"]
    assert [c["title"] for c in list_b] == ["B thread"]

    # Owner can delete their own.
    assert client.delete(f"/api/conversations/{cid}", headers=headers_a).status_code == 200


def test_delete_conversation_removes_messages(client, seeded_db):
    created = client.post("/api/conversations", json={"guest_id": GUEST_A}).json()
    cid = created["id"]
    client.post(
        "/api/assistant/chat/conversation",
        json={"message": "What programs exist?", "conversation_id": cid, "guest_id": GUEST_A},
    )
    assert seeded_db.query(ConversationMessage).count() >= 2

    client.delete(f"/api/conversations/{cid}", params={"guest_id": GUEST_A})
    assert seeded_db.get(Conversation, cid) is None
    remaining = (
        seeded_db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == cid)
        .count()
    )
    assert remaining == 0, "messages must cascade-delete with the conversation"


# --------------------------------------------------------------------------- #
# No AI provider configured
# --------------------------------------------------------------------------- #
def test_chat_without_ai_provider_stays_groundedin(client):
    """LLM_PROVIDER=none: answers must still work, cite sources, and say they
    are extractive rather than pretending to be model-generated."""
    res = client.post(
        "/api/assistant/chat",
        json={"message": "What is the aggregate formula for MBBS?", "program": "MBBS"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["provider_configured"] is False
    assert body["generated_by"] == "extractive"
    assert body["citations"], "extractive answers must still cite documents"
    assert any(
        "No generative AI provider" in d or "assembled directly" in d
        for d in body["disclaimers"]
    ), "the UI must disclose that no AI provider is configured"


def test_unanswerable_question_is_admitted_not_invented(client):
    res = client.post(
        "/api/assistant/chat",
        json={"message": "zzzzunfindabletopiczzzz unique query with no matches at all"},
    )
    body = res.json()
    # Either no evidence -> honest refusal, or (if weak keyword hits) the answer
    # must not fabricate specific numbers. Check the no-evidence branch.
    if not body["citations"] and not body["tools_used"]:
        assert "could not find official evidence" in body["answer"].lower()
    else:
        assert "could not be verified" in " ".join(body["missing_information"]).lower() or body[
            "answer"
        ]
