#!/usr/bin/env bash
#
# Levanta TODA la app en local, sin Docker:
#   Postgres (pgserver) -> migraciones -> backend (uvicorn :8000) -> frontend (vite :5173)
#
# Uso:   ./scripts/dev.sh
# Cortar con Ctrl-C: apaga el backend y el Postgres automáticamente.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

db() { uv run --project "$ROOT/server" python "$ROOT/scripts/db.py" "$@"; }

echo "==> Postgres (pgserver, sin Docker)…"
DATABASE_URL="$(db url)"
export DATABASE_URL
echo "    $DATABASE_URL"

echo "==> Migraciones…"
( cd server && uv run alembic upgrade head )

echo "==> Backend (uvicorn :8000)…"
( cd server && exec uv run uvicorn app.main:app --reload --port 8000 ) &
BACKEND_PID=$!

LIMPIO=0
limpiar() {
  [ "$LIMPIO" = 1 ] && return
  LIMPIO=1
  echo
  echo "==> Deteniendo…"
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
echo "    backend OK — docs en http://localhost:8000/docs"

echo "==> Frontend (vite :5173)… (Ctrl-C para cortar todo)"
cd client
[ -d node_modules ] || npm install
exec npm run dev
