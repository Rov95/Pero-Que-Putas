# Pero Qué Putas — Backend

FastAPI + PostgreSQL + WebSockets backend for **Pero Qué Putas**, a Spanish-language
"¿qué prefieres?" (would-you-rather) party game played in real time in **salas** (rooms)
identified by a 6-character invite code.

For the full API reference (REST + WebSocket protocol, wire shapes, game rules, edge cases)
see [`~/Desktop/Context/PQP/backend-api.md`](../../../Context/PQP/backend-api.md) — this README
only covers getting the server running.

## Requirements

- **Python 3.12** (pinned via `.python-version`; the project uses async DB drivers that need
  this version specifically — a newer system Python may fail to build some wheels).
- **[uv](https://docs.astral.sh/uv/)** — manages the virtualenv and dependencies from
  `pyproject.toml`/`uv.lock`. Install it if you don't have it:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **PostgreSQL 16**, reachable at the URL in `.env`. Two ways to get one:
  - **Docker** (recommended for normal dev) — a `docker-compose.yml` is included.
  - **No Docker available?** The test suite itself never needs Docker — it spins up a real,
    disposable Postgres via the `pgserver` PyPI package (a self-contained Postgres binary,
    no root required). You can use the same trick for local dev in a sandbox/CI box that has
    no Docker and no system Postgres; see [Running without Docker](#running-without-docker-sandboxci) below.

## Setup

From this directory (`server/`):

```bash
# 1. Start Postgres
docker compose up -d
#    → postgres:16 on localhost:5432, db/user/password all "pero_que_putas"

# 2. Configure environment
cp .env.example .env
#    .env already matches the docker-compose credentials by default; edit
#    CORS_ORIGINS if your frontend runs somewhere other than http://localhost:5173

# 3. Install dependencies (creates .venv automatically)
uv sync

# 4. Apply database migrations
uv run alembic upgrade head

# 5. Run the API
uv run uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`, with interactive Swagger docs at
`http://localhost:8000/docs`.

### Seed data caveat

The database starts with **zero preguntas** (dilemma cards). A game cannot draw a card
until at least one exists. Create some via `POST /api/preguntas` (from `/docs`, `curl`, or
the frontend's card-creation screen), e.g.:

```bash
curl -X POST http://localhost:8000/api/preguntas \
  -H "Content-Type: application/json" \
  -d '{"opcion_1": "Tener que cantar antes de cada comida", "opcion_2": "Tener que bailar antes de cada comida"}'
```

## Running the tests

```bash
uv run pytest
```

Tests need **no Docker and no running Postgres** — `tests/conftest.py` spins up a real,
temporary Postgres instance per session via `pgserver` and tears it down afterward.

## Running without Docker (sandbox/CI)

If Docker isn't available, use the repo's helper to run Postgres via `pgserver` (a
self-contained Postgres binary, no root, no Docker — the same trick the tests use).
**This is the fix if `docker compose up -d` above failed because Docker isn't installed.**
From the repo root:

```bash
# start Postgres and capture the connection string in one go:
export DATABASE_URL="$(uv run --project server python scripts/db.py start)"

# then, from server/, migrate and run the API as usual:
cd server
uv run alembic upgrade head
DATABASE_URL="$DATABASE_URL" uv run uvicorn app.main:app --reload --port 8000
```

Stop it later with `uv run --project server python scripts/db.py stop`. The DB is a real
background daemon (data under `<repo>/.local/pgdata`) reached over a Unix socket, so the
`DATABASE_URL` looks like `postgresql+asyncpg://postgres:@/postgres?host=<repo>/.local/pgdata`
instead of `localhost:5432`. See [`scripts/db.py`](../scripts/db.py) for `start | url | stop | status`.

Even simpler: from the repo root, **[`./scripts/dev.sh`](../scripts/dev.sh)** does all of the
above *and* starts the frontend. This is a dev/CI convenience — `docker-compose.yml` remains
the supported path on a normal machine.

## Environment variables

Set in `.env` (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://pero_que_putas:pero_que_putas@localhost:5432/pero_que_putas` | Async SQLAlchemy connection string |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of allowed frontend origins |
| `BOTS_RETRASO_MIN_MS` | `800` | Lower bound of the random delay before a bot sends robar_carta/prediccion/voto |
| `BOTS_RETRASO_MAX_MS` | `2500` | Upper bound of that same delay |
| `BOTS_RETRASO_SIGUIENTE_TURNO_MS` | `4000` | Base delay (before jitter, up to `BOTS_RETRASO_MAX_MS` extra) before a bot-lector sends `siguiente_turno`, so the human has time to read the round result |
| `BOTS_VIDA_MAXIMA_SEGUNDOS` | `1800` | Hard cap on how long a bot's WS task stays alive (abandoned practice room cleanup) |

## Modo práctica

`POST /api/salas/practica` (body `{"usuario_id": "<uuid>"}`) creates a sala with that
user as anfitrión, generates 2 `Bot-<Apodo>-<sufijo>` users, joins them, and launches one
in-process WebSocket client task per bot (`app/bots/`) — real WS connections against the
app's own ASGI callable via `httpx_ws` + `ASGIWebSocketTransport`, not a simulation. Each
bot follows a fixed reaction table (see `app/bots/jugador.py`): uniformly random
prediction/vote, small randomized delays (`BOTS_RETRASO_*` above) before every action, and
terminates cleanly on `partida_finalizada`, on its own WS closing, or when
`BOTS_VIDA_MAXIMA_SEGUNDOS` elapses (whichever first) — never via a hard task
cancellation while the socket is open, since that was found to corrupt the shared
DB connection pool (see the comment on `INTERVALO_SONDEO_SEGUNDOS` in `jugador.py`).

`app/bots/registro.py` tracks the running tasks per sala (`RegistroBots`); the app's
`lifespan` stops all of them on shutdown. Returns 409 (same shape as every other error,
`{"detalle": "..."}`) if the sala has zero preguntas — a practice game can't draw a card
either.

Bots are ordinary `usuarios` and `sala_jugadores` rows: they show up in the lobby's player
list like anyone else, and `finalizar` writes their rows into `marcador_historico` same as
a human's — accepted as the simplest option since this is a dev/practice tool, not
something the historic scoreboard needs to filter.

## Project layout

```
server/
├── app/
│   ├── main.py           # create_app(), router registration, exception handlers
│   ├── config.py         # Settings: DATABASE_URL, CORS_ORIGINS (.env)
│   ├── constants.py      # PrediccionEnum, ResultadoEnum, Estado*Enum + Spanish labels
│   ├── errores.py         # ErrorAplicacion(detalle, status_code)
│   ├── manejadores.py    # global exception handlers → {"detalle": "..."} bodies
│   ├── models/           # SQLAlchemy: usuario, pregunta(+opcion), sala(+sala_jugador), ronda(+voto), marcador
│   ├── schemas/          # Pydantic request/response models
│   ├── routers/          # usuarios, preguntas, constantes, salas, puntos (thin HTTP handlers)
│   ├── services/         # all game rules: salas.py, juego.py, preguntas.py, usuarios.py, marcador.py
│   └── websocket/
│       ├── manager.py    # in-memory {codigo: {usuario_id: WebSocket}} connection registry
│       ├── router.py     # WS endpoint + event dispatch
│       └── eventos.py    # event names + payload builders
├── alembic/               # migrations (script_location = alembic/)
├── tests/                 # pytest suite, uses pgserver — no Docker needed
├── docker-compose.yml     # Postgres 16 for local dev
└── pyproject.toml / uv.lock
```

## Notes on the game itself

There is **no authentication** — the client identifies itself by passing `usuario_id` in
request bodies and the WebSocket query string (`?usuario_id=...`); the frontend is expected
to persist that ID (e.g. `localStorage`) once a user is created. Every error response, at
any status code, has the same shape: `{"detalle": "<mensaje en español>"}`.

See [`~/Desktop/Context/PQP/backend-api.md`](../../../Context/PQP/backend-api.md) for the
complete REST + WebSocket contract, the round state machine, and known edge cases (deck
exhaustion, ties, reconnection behavior, disconnection rules).
