#!/bin/sh
# Container entrypoint: seed the knowledge base once, then start the API.
#
# Seeding is idempotent — it only runs when the SQLite database has no
# documents yet. It uses the committed data/raw/ archive (offline), so startup
# never depends on external network access. Any failure is non-fatal: the API
# still boots and reports an empty knowledge base in /api/health.
set -e

cd /app/backend

echo "[entrypoint] initialising database and seeding knowledge base (offline)..."
python -m app.cli bootstrap --offline || echo "[entrypoint] bootstrap skipped/failed; starting API anyway"

echo "[entrypoint] starting API on 0.0.0.0:${PORT:-8010}"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8010}"
