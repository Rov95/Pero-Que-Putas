#!/usr/bin/env bash
#
# Test end-to-end de TODA la app, sin Docker:
#   arranca Postgres (pgserver) -> migraciones -> backend (uvicorn) ->
#   Playwright (que arranca el frontend con Vite y juega una partida completa
#   con 3 navegadores) -> apaga todo.
#
# Uso:   ./scripts/e2e.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

db() { uv run --project "$ROOT/server" python "$ROOT/scripts/db.py" "$@"; }

echo "==> Postgres (pgserver, sin Docker)…"
DATABASE_URL="$(db url)"
export DATABASE_URL

echo "==> Migraciones…"
( cd server && uv run alembic upgrade head )

echo "==> Backend (uvicorn :8000)…"
( cd server && exec uv run uvicorn app.main:app --port 8000 --log-level warning ) &
BACKEND_PID=$!

LIMPIO=0
limpiar() {
  [ "$LIMPIO" = 1 ] && return
  LIMPIO=1
  echo "==> Limpiando…"
  kill "$BACKEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
  db stop || true
}
trap limpiar EXIT INT TERM

echo "==> Esperando al backend…"
for _ in $(seq 1 60); do
  if curl -sf http://localhost:8000/api/salud >/dev/null 2>&1; then break; fi
  sleep 0.5
done
curl -sf http://localhost:8000/api/salud >/dev/null 2>&1 || { echo "El backend no arrancó"; exit 1; }

echo "==> Playwright (frontend + partida completa)…"
cd client
[ -d node_modules ] || npm install
npm run test:e2e
