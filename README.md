# MAHSUDo-guide

Conversational AI guidance platform for Khyber Medical University (KMU),
Peshawar admissions. FastAPI + SQLite backend, React + TypeScript frontend.

## Architecture

Two interfaces share one backend, so they can be deployed independently:

```
backend/                 FastAPI app (the single source of truth)
  app/
    api/                 assistant (chat, /api/time), conversations, search, admin, auth
    services/            agent (orchestration), retrieval (hybrid search), ingest, llm
    utils/time.py        Asia/Karachi clock helpers (never hardcoded dates)
    models.py            Conversation, ConversationMessage, Document, Chunk, User, ...
  alembic/               migrations (conversations + conversation_messages)
  tests/                 pytest suite (63 tests)
frontend/                React 19 + Vite SPA; calls the backend at "/api"
streamlit_app.py         alternative single-file UI reusing backend services directly

data/raw/                committed official-source archive used to seed the KB offline
Dockerfile               container for the Streamlit interface
Dockerfile.fullstack     container that builds the SPA and serves it + the API together
render.yaml              Render Blueprint (both services)
```

- **Full-stack (recommended)** — one process. `backend/app/main.py` mounts
  `frontend/dist` at `/` when a production build exists, so the SPA and the API
  share an origin and no CORS or API-base configuration is needed.
- **Streamlit** — one process, no separate frontend build; reuses the same
  agent, retrieval and clock code.

### Which platform?

| Platform | Best for | Notes |
| --- | --- | --- |
| **Render** (Blueprint) | Full-stack or Streamlit | `render.yaml` is ready; free tier sleeps when idle |
| **Streamlit Community Cloud** | Streamlit UI only | simplest; Streamlit-only, ephemeral disk |
| **Docker anywhere** (Fly, Railway, VPS) | Full control | use `Dockerfile.fullstack` |
| **Local** | Development | see "Running" below |

SQLite is used by default. On platforms with ephemeral disks (Render free,
Streamlit Cloud) chat history resets on redeploy — set `DATABASE_URL` to a
PostgreSQL instance for persistence.

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
| `gemini`           | `https://generativelanguage.googleapis.com/v1beta/openai`  | `gemini-3.5-flash-lite`                | `GEMINI_API_KEY`    |
| `groq`             | `https://api.groq.com/openai/v1`                           | `openai/gpt-oss-20b`                   | `GROQ_API_KEY`      |
| `openrouter`       | `https://openrouter.ai/api/v1`                             | `meta-llama/llama-3.2-3b-instruct:free`| `OPENROUTER_API_KEY`|
| `openai`           | `https://api.openai.com/v1` (or `LLM_BASE_URL`)            | `gpt-4o-mini`                          | `OPENAI_API_KEY`    |
| `openai_compatible`| your `LLM_BASE_URL`                                        | your `LLM_MODEL`                       | `LLM_API_KEY`       |
| `ollama`           | `OLLAMA_BASE_URL` (local)                                  | your `LLM_MODEL`                       | n/a                 |

### Google Gemini model choice

Gemini free-tier limits are per model, and Google currently restricts the 2.5
family to accounts that already used it, so **new projects must use a 3.x model**
(<https://ai.google.dev/gemini-api/docs/models>):

| Model                  | Free tier (approx.)  | When to use                          |
| ---------------------- | -------------------- | ------------------------------------ |
| `gemini-3.5-flash-lite`| 500 req/day, 15 RPM  | Default — best quota for public use  |
| `gemini-3.8-flash`     | ~20 req/day, 5 RPM   | Higher quality, easy to exhaust      |

Set `LLM_MODEL` in `.env` to switch. Rate limits are per project, reset at
midnight Pacific time, and are visible in Google AI Studio
(<https://aistudio.google.com>).

Recommendation for this project: start with **Google Gemini** (free tier plus an
OpenAI-compatible endpoint; see <https://ai.google.dev/gemini-api/docs/openai>),
or **Groq** for low latency. **Local Ollama is only practical with roughly 8 GB+
RAM and a GPU** — the reference deployment here has ~4 GB RAM, so hosted
providers are recommended.

To enable a provider (settings are read from `.env` in the repo root **or**
`backend/`; real environment variables always take precedence):

```
# .env   (repo root)
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

### Backend (from `backend/`)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.cli bootstrap --offline     # create DB + seed from data/raw (no network)
python -m uvicorn app.main:app --reload --port 8010
```

API docs: <http://127.0.0.1:8010/docs> · health: <http://127.0.0.1:8010/api/health>

### Frontend (from `frontend/`)

```powershell
npm install
npm run dev      # http://127.0.0.1:5173 (proxies /api to the backend on 8010)
```

The dev proxy target defaults to `http://127.0.0.1:8010`. Override it with
`VITE_API_PROXY_TARGET` if the backend runs elsewhere (see `frontend/.env.example`).

### Single-origin production (no separate frontend server)

```powershell
cd frontend; npm run build          # emits frontend/dist
cd ..\backend; python -m uvicorn app.main:app --port 8010
```

The API detects `frontend/dist/index.html` and serves the SPA at `/`, so the
whole app is reachable at <http://127.0.0.1:8010>.

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

1. Push this repository to GitHub.
2. Go to <https://share.streamlit.io> and sign in with GitHub.
3. Click **Create app** → **Deploy a public app from GitHub**, then set:
   - **Repository**: your repo (e.g. `maseedwasimullah-crypto/mahsud-guide`)
   - **Branch**: `master`
   - **Main file path**: `streamlit_app.py`
4. Open **Advanced settings → Secrets** and paste the keys you need, for example:

   ```toml
   SECRET_KEY = "<long random string>"
   LLM_PROVIDER = "gemini"
   GEMINI_API_KEY = "<your-key>"
   ```

   `.streamlit/secrets.toml.example` lists every supported key. The app bridges
   these secrets into the backend settings at startup (`streamlit_app.py`), so no
   code changes are required. Secrets are provided by Streamlit at runtime and
   are never written to the repository (`.streamlit/secrets.toml` is git-ignored).
5. Click **Deploy**. Streamlit Cloud installs `requirements.txt` from the repo
   root automatically.

Notes:

- Without an `LLM_PROVIDER`/key the app still runs in extractive mode (grounded
  answers from `data/raw/`), so a missing key is not fatal.
- The knowledge base is bootstrapped from the committed `data/raw/` archive on
  first run; the SQLite database lives on the app's ephemeral filesystem, so
  chat history resets when the app is rebuilt or restarted. Use an external
  database (`DATABASE_URL`) if persistence is required.
- Set `SECRET_KEY` in Secrets so login tokens are stable across restarts.

### Deploying with Docker or Render

Two Dockerfiles are provided:

| File | Serves | Port | Health check |
| --- | --- | --- | --- |
| `Dockerfile.fullstack` | React SPA **+** FastAPI (recommended) | `8010` | `/api/health` |
| `Dockerfile` | Streamlit assistant | `8501` | `/_stcore/health` |

Both seed the knowledge base from the committed `data/raw/` archive at boot, so
they work without outbound network access.

```powershell
# Full-stack image
docker build -t mahsud-guide-full -f Dockerfile.fullstack .
docker run -p 8010:8010 `
  -e SECRET_KEY=change-me `
  -e LLM_PROVIDER=gemini -e GEMINI_API_KEY=your-key `
  mahsud-guide-full
# -> http://localhost:8010

# Streamlit image
docker build -t mahsud-guide .
docker run -p 8501:8501 -e LLM_PROVIDER=gemini -e GEMINI_API_KEY=your-key mahsud-guide
# -> http://localhost:8501
```

Render (Blueprint) — deploy both/one from `render.yaml`:

1. Push this repo to GitHub.
2. Render dashboard → **New → Blueprint** → pick this repo → **Apply**. Render
   generates `SECRET_KEY` automatically and prompts for provider keys.
3. CLI alternative: `pip install render-cli && render login && render blueprint launch`.

Delete the service you do not need from `render.yaml` (use the full-stack
`mahsud-guide` for the React app, or `mahsud-guide-streamlit` for the Streamlit
UI). Leave `LLM_PROVIDER=none` for extractive answers or set a provider + key
for model-written answers.

## Testing

```
cd backend && python -m pytest -q     # 63 tests: API, retrieval, timezone, conversations, LLM providers
cd frontend && npm run build          # tsc typecheck + vite production build
cd frontend && npm run lint           # oxlint
```

Timezone tests use controlled UTC instants (including dates where the UTC
calendar day differs from Pakistan's) so results are deterministic.
Conversation tests cover ownership isolation (guest and authenticated),
follow-up retrieval, cascade delete, and the no-provider extractive path.

## Configuration

Settings are read from real environment variables first, then from the first
`.env` found in the repo root or `backend/`. `.env.example` lists every variable.

### Required in production

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Signs auth tokens. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `LLM_PROVIDER` | `none` (extractive) or `gemini` / `groq` / `openrouter` / `openai` / `openai_compatible` / `ollama`. |
| provider key | `<PROVIDER>_API_KEY` or the generic `LLM_API_KEY` matching `LLM_PROVIDER`. |

### Common optional

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | local SQLite | Use `postgresql+psycopg://…` for persistence on ephemeral hosts. |
| `LLM_MODEL` | provider default | e.g. `gemini-3.5-flash-lite`, `gemini-3.8-flash`. |
| `ALLOWED_ORIGINS` | localhost:5173 | Comma-separated CORS origins (needed only for a separately hosted frontend). |
| `ENVIRONMENT` | `development` | Set `production` on live hosts. |
| `ADMIN_SEED_EMAIL` / `ADMIN_SEED_PASSWORD` | — | Used by `python -m app.cli create-admin`. |
| `VITE_API_BASE_URL` | `/api` | Frontend build-time API origin when not served from the same host. |

Frontend variables must be prefixed `VITE_` and are baked in at build time
(`frontend/.env.example`).

Never commit secrets: `.env`, `.streamlit/secrets.toml` and `*.key`/`*.pem` are
git-ignored (see `.gitignore`). Provider error messages returned to the client
are redacted.
