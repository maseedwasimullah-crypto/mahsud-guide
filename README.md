# MAHSUDo-guide

Conversational AI guidance platform for Khyber Medical University (KMU),
Peshawar admissions. FastAPI + SQLite backend, React + TypeScript frontend.

## Architecture

```
backend/
  app/
    api/            assistant (chat, /api/time), conversations, search, admin, auth
    services/       agent (orchestration), retrieval (hybrid search), ingest, llm
    utils/time.py   Asia/Karachi clock helpers (never hardcoded dates)
    models.py       Conversation, ConversationMessage, Document, Chunk, User, ...
  alembic/          migrations (conversations + conversation_messages)
  tests/            pytest suite (51 tests)
frontend/
  src/pages/Assistant.tsx   chat UI: sidebar, message bubbles, citations
  src/components/Clock.tsx  live Peshawar clock, synced to /api/time
```

## Conversational assistant

- `POST /api/assistant/chat` — stateless chat; accepts inline `history` for
  follow-up context. Search queries merge the previous user turn with the
  current message so follow-ups like "what about eligibility?" still retrieve.
- `POST /api/assistant/chat/conversation` — stateful chat bound to a
  conversation id; persists both turns and reuses stored history for retrieval.
- `GET /api/time` — live server time in Asia/Karachi (UTC+5, no DST). The
  assistant's system prompt embeds this on every turn; the frontend clock
  polls it every 60s.

## Conversation storage

- Authenticated: conversations keyed by `user_id`; only the owner can
  list/read/delete (404 for anyone else, including other logged-in users).
- Guest mode: the frontend generates a random UUID stored in
  `localStorage`; conversations are keyed by `guest_id`. No personal data is
  collected. A conversation without `user_id` or `guest_id` is rejected.
- Messages cascade-delete with their conversation.

## Grounding and honesty

- Retrieval blends BM25-style lexical scores with embedding cosine similarity.
  Chunks below `MIN_EVIDENCE_SCORE` (0.1) are dropped so unrelated documents
  are never presented as evidence — the agent says "could not find official
  evidence" and points to the official source instead.
- Every answer cites document title, source URL, publication date, and
  retrieval date. Disclaimers mark demo data, conflicting sources, and
  historical documents.
- With `LLM_PROVIDER=none` (default), answers are extractive (assembled from
  retrieved excerpts, `generated_by=extractive`) and the UI discloses that no
  generative provider is configured. Set `LLM_PROVIDER=openai` +
  `OPENAI_API_KEY` to enable model-written answers that still require
  retrieved evidence.

## Running

Backend (from `backend/`):

```
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env                           # set SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend (from `frontend/`):

```
npm install
npm run dev
```

## Testing

```
cd backend && python -m pytest -q     # 51 tests: API, retrieval, timezone, conversations
cd frontend && npx tsc --noEmit       # typecheck
cd frontend && npx oxlint            # lint
```

Timezone tests use controlled UTC instants (including dates where the UTC
calendar day differs from Pakistan's) so results are deterministic.
Conversation tests cover ownership isolation (guest and authenticated),
follow-up retrieval, cascade delete, and the no-provider extractive path.

## Configuration

`.env.example` lists all variables. Sensitive values (SECRET_KEY,
OPENAI_API_KEY, ADMIN_EMAIL, ADMIN_PASSWORD) stay in environment variables
only and are never committed.
