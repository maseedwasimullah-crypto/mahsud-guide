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
  tests/            pytest suite (63 tests)
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
  generative provider is configured.
- When a provider *is* configured but cannot be reached (bad key, quota,
  network), the answer falls back to extractive text and states the reason in
  the disclaimers and in the `provider_error` field — it never silently
  pretends a model answered. Secrets are redacted from those messages.

## Choosing an AI provider

Model-written answers require a provider; every hosted option below uses the
same OpenAI-compatible Chat Completions protocol, so no code changes are needed.

| `LLM_PROVIDER`     | Endpoint (official)                                        | Default model                          | Key variable        |
| ------------------ | ---------------------------------------------------------- | -------------------------------------- | ------------------- |
| `gemini`           | `https://generativelanguage.googleapis.com/v1beta/openai`  | `gemini-2.5-flash`                     | `GEMINI_API_KEY`    |
| `groq`             | `https://api.groq.com/openai/v1`                           | `openai/gpt-oss-20b`                   | `GROQ_API_KEY`      |
| `openrouter`       | `https://openrouter.ai/api/v1`                             | `meta-llama/llama-3.2-3b-instruct:free`| `OPENROUTER_API_KEY`|
| `openai`           | `https://api.openai.com/v1` (or `LLM_BASE_URL`)            | `gpt-4o-mini`                          | `OPENAI_API_KEY`    |
| `openai_compatible`| your `LLM_BASE_URL`                                        | your `LLM_MODEL`                       | `LLM_API_KEY`       |
| `ollama`           | `OLLAMA_BASE_URL` (local)                                  | your `LLM_MODEL`                       | n/a                 |

Recommendation for this project: start with **Google Gemini** (Gemini offers a
free tier and an OpenAI-compatible endpoint; see
<https://ai.google.dev/gemini-api/docs/openai>), or **Groq** for low latency.
**Local Ollama is only practical with roughly 8 GB+ RAM and a GPU** — the
reference deployment here has ~4 GB RAM, so hosted providers are recommended.

To enable a provider:

```
# backend/.env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
# LLM_MODEL=            # optional: omit to use the default model
```

Then verify credentials with a tiny live call (exit code 0 = connected):

```
cd backend && python -m app.cli llm-check
```

Notes and caveats (verify against each provider's current terms before relying
on them):

- Free tiers exist but have per-minute/per-day request and token limits, and
  limits change over time. Check the provider's official pricing/rate-limit page.
- Some free tiers (for example Google's free tier for Gemini) may use submitted
  content to improve products. Review the provider's data-use policy and do not
  send sensitive data.
- `LLM_API_KEY` is a generic variable that overrides the provider-specific key.
- Set `LLM_TEMPERATURE` (default `0.1`) and `LLM_TIMEOUT_SECONDS` (default `90`)
  if you need to tune generation.

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

## Streamlit interface

`streamlit_app.py` (repo root) exposes the same conversational assistant as a
Streamlit app — same retrieval, citations, follow-up context and Peshawar
clock, reusing the backend services directly (no API server required):

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

It bootstraps the database and seeds the knowledge base from `data/raw/` on
first run if the database is empty.

### Deploying to Streamlit Community Cloud

1. Fork/push this repository to GitHub.
2. Go to <https://share.streamlit.io>, sign in with GitHub, pick this repo,
   set the main file path to `streamlit_app.py`.
3. Streamlit Cloud installs `requirements.txt` from the repo root
   automatically; no other configuration is needed.

The app runs in extractive mode (`LLM_PROVIDER=none` by default). To enable
model-written answers, add `LLM_PROVIDER=gemini` and `GEMINI_API_KEY` (or any
other provider/key pair from the table above) in the Streamlit Cloud
secrets/environment settings.

## Testing

```
cd backend && python -m pytest -q     # 63 tests: API, retrieval, timezone, conversations, LLM providers
cd frontend && npx tsc --noEmit       # typecheck
cd frontend && npx oxlint            # lint
```

Timezone tests use controlled UTC instants (including dates where the UTC
calendar day differs from Pakistan's) so results are deterministic.
Conversation tests cover ownership isolation (guest and authenticated),
follow-up retrieval, cascade delete, and the no-provider extractive path.

## Configuration

`.env.example` lists all variables. Sensitive values (SECRET_KEY,
GEMINI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY / OPENAI_API_KEY / LLM_API_KEY,
ADMIN_EMAIL, ADMIN_PASSWORD) stay in environment variables only and are never
committed. Provider error messages returned to the client are redacted.
