# Pero Qué Putas — Full App Context

> **Purpose of this file:** whole-app map of `~/Desktop/Portfolio/Pero-Que-Putas` so a
> Claude agent can orient itself **without scanning the project**. Read this first, then
> drill into the layer doc you need:
>
> - [`backend-api.md`](backend-api.md) — the full REST + WebSocket contract (endpoints,
>   payloads, errors, round state machine). **Read it before touching anything that talks
>   to the server.**
> - [`frontend.md`](frontend.md) — the React client: screens, Redux slices, WS middleware,
>   conventions, known gotchas.
>
> Verified against the code on branch `main` as of 2026-07-15. Status: backend (10 phases)
> and frontend (5 phases) fully implemented and verified end-to-end; ~61 pytest + 27 vitest
> tests and a 3-browser Playwright E2E, all green.

---

## 1. The game (domain, 30 seconds)

Spanish-language Colombian party game, "¿qué prefieres?" style. Everything user-facing —
and **every identifier in the codebase** (models, actions, routes, variables) — is in
Spanish.

1. Players register a **username** (no auth — identity is a stored `usuario_id` UUID).
2. They gather in a **sala** (room) via a 6-char **codigo** (alphabet without 0/O/1/I/L).
   The creator is the **anfitrión** (host).
3. Host starts the game → players get a shuffled **orden_turno**. Each round one player is
   the **lector**: draws a **pregunta** (card with two absurd options), makes a **secret
   prediction** of the group vote (`mayoria_1 | todos_1 | mayoria_2 | todos_2`), then
   everyone else votes 1 or 2.
4. The round auto-resolves when the last expected vote arrives (only *connected*
   non-lector players are expected). Result: `todos_X` / `mayoria_X` / `empate`.
   Prediction matching is **strict** (`mayoria_1` ≠ `todos_1`); a hit gives the lector
   **1 punto**; on empate nobody scores. Lector never votes.
5. Turn passes (`siguiente_turno`, by lector or host). Game ends when the **host**
   finalizes: points move to an all-time **marcador histórico** (ties → multiple winners),
   sala becomes `finalizada` (dead — new game means new sala).

Cards are user-created content: **the DB starts with zero preguntas**; the game cannot
play a round until someone creates cards at `/preguntas`.

## 2. Architecture

```
┌─────────────────────┐   REST /api/*  (join, start, finish, CRUD, scoreboard)
│  Browser (React 19) │ ───────────────────────────►  ┌────────────────────┐      ┌───────────────┐
│  Vite dev :5173     │                               │  FastAPI (uvicorn) │ ───► │ PostgreSQL 16 │
│  Redux Toolkit      │ ◄───────────────────────────► │  :8000             │ ◄─── │ (pgserver or  │
│  WS middleware      │   WebSocket /ws/salas/{codigo}│  async SQLAlchemy  │      │  Docker)      │
└─────────────────────┘   (all in-game actions)       └────────────────────┘      └───────────────┘
```

- **Split of responsibilities**: lobby/lifecycle actions (create/join/start/finish) and all
  CRUD go over **REST**; everything inside a round (`robar_carta`, `prediccion_secreta`,
  `voto`, `siguiente_turno`) goes over the **WebSocket** as `{evento, datos}` envelopes,
  and the server broadcasts game events to the whole sala.
- **Identity**: no auth anywhere. The client persists `usuario_id` in localStorage and
  sends it in request bodies / the WS query string. Usernames are globally unique
  (case-insensitive) — losing the id means the name is unrecoverable (409 on re-create).
- **Reconnection contract**: `GET /api/salas/{codigo}` is the resync snapshot; the client
  always re-fetches it before reopening a dropped socket. The snapshot does NOT include
  the active round's stage/card (known limitation, see §7).
- **Errors**: every REST error body, any status, is `{"detalle": "<Spanish message>"}`.
  WS business-rule violations never close the socket — the server replies an `error`
  event to the offending socket only. WS close code **4003** = expelled (not a member /
  sala gone).
- **Secrecy invariants**: individual votes and the lector's prediction are never
  observable (REST or WS) before the `resultado_ronda` reveal.

## 3. Repo layout (monorepo)

```
Pero-Que-Putas/
├── Context/
│   ├── PQP/                 # ← agent context docs (this file, backend-api.md, frontend.md)
│   └── plans/               # implementation plans (backend, frontend, práctica)
├── scripts/
│   ├── db.py                # local Postgres WITHOUT Docker via pgserver (start|url|stop|status)
│   ├── dev.sh               # one command: db + migrations + backend :8000 + frontend :5173
│   └── e2e.sh               # full-stack E2E: db + backend + Playwright (3 browsers), then teardown
├── server/                  # FastAPI backend  → details: Context/PQP/backend-api.md, server/README.md
│   ├── app/
│   │   ├── main.py          # create_app(), routers, exception handlers
│   │   ├── config.py        # Settings: DATABASE_URL, CORS_ORIGINS (.env)
│   │   ├── constants.py     # enums + Spanish labels (predictions, estados)
│   │   ├── errores.py / manejadores.py   # ErrorAplicacion → {"detalle"} bodies
│   │   ├── models/          # SQLAlchemy: usuario, pregunta(+opcion), sala(+sala_jugador),
│   │   │                    #   ronda(+voto), marcador_historico
│   │   ├── schemas/         # Pydantic v2 request/response
│   │   ├── routers/         # thin: usuarios, preguntas, constantes, salas, puntos
│   │   ├── services/        # ALL game rules: salas.py, juego.py, preguntas.py, usuarios.py, marcador.py
│   │   └── websocket/       # manager.py (in-memory sockets per sala), router.py (dispatch), eventos.py
│   ├── alembic/             # migrations (single initial schema revision)
│   ├── tests/               # pytest ×12 files (~61 tests) — spin up real Postgres via pgserver
│   ├── docker-compose.yml   # optional Postgres 16 for those with Docker
│   └── pyproject.toml       # uv-managed, Python 3.12
├── client/                  # React frontend  → details: Context/PQP/frontend.md, client/README.md
│   ├── src/                 # (see frontend.md §3 for the full map)
│   ├── e2e/juego-completo.spec.ts   # Playwright: 3 browsers play a whole game
│   └── package.json         # Vite 8, React 19, RTK 2, Tailwind 4, Vitest, Playwright
└── README.md                # user-facing quickstart (Spanish)
```

## 4. Tech stack summary

| Layer | Stack |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 async · PostgreSQL 16 · Alembic · Pydantic v2 · uvicorn · native FastAPI WebSockets · pytest (+pgserver embedded Postgres) · managed by **uv**, Python 3.12 |
| Frontend | React 19 · TypeScript strict · Vite 8 (:5173) · Redux Toolkit 2 (WS as middleware) · react-router-dom 7 · Tailwind CSS v4 (dark, mobile-first) · Vitest · Playwright (system Chrome) |
| Glue | REST under `/api`, WS under `/ws`, base `http://localhost:8000`; CORS default allows `http://localhost:5173`; frontend env `VITE_API_URL` |

## 5. Data model (5 core tables + join/detail tables)

- `usuarios` — id (UUID), username (unique, case-insensitive), creado_en.
- `preguntas` + `opciones` — a card and its exactly-2 options (cascade delete).
- `salas` + `sala_jugadores` — room (codigo, estado `esperando|en_curso|finalizada`,
  anfitrion_id, `turno_actual` raw counter) and membership (orden_turno, puntos,
  conectado). **Lector = jugador whose `orden_turno == turno_actual % n_jugadores`** —
  both sides compute it this way, never store it.
- `rondas` + `votos` — one round per drawn card (estado `leyendo|votando|resuelta`,
  prediccion, resultado); votes are unique per (ronda, usuario). Preguntas never repeat
  within a sala.
- `marcador_historico` — one row per player per finished game (puntos_finales, gano).

## 6. The contract in one glance

(Exact payloads, status codes, and error strings: `backend-api.md` §4–§5.)

**REST**: `POST /api/usuarios` · `GET /api/usuarios/{id}` · preguntas CRUD
(`GET/POST /api/preguntas`, `GET/PUT …/{id}/opciones`, `DELETE …/{id}`) ·
`GET /api/constantes/predicciones` · `POST /api/salas` · `POST /api/salas/{codigo}/unirse`
(idempotent) · `GET /api/salas/{codigo}` (resync snapshot) ·
`POST /api/salas/{codigo}/iniciar` (host) · `POST /api/salas/{codigo}/finalizar` (host;
atomic: historic rows + reset + estado) · puntos utilities
(`GET/PUT/DELETE /api/salas/{codigo}/puntos…`) · `GET /api/marcador`.

**WS** `ws://…/ws/salas/{codigo}?usuario_id=…` — client sends: `robar_carta`,
`prediccion_secreta`, `voto`, `siguiente_turno`. Server broadcasts: `jugador_unido`,
`jugador_salio`, `partida_iniciada`, `turno_actual`, `carta_robada`,
`prediccion_registrada`, `voto_registrado` (n/m progress, anonymous),
`resultado_ronda` (the reveal), `partida_finalizada`, plus per-socket `error`.

**Round state machine**: `(no round)` →robar_carta→ `leyendo` →prediccion_secreta→
`votando` →last expected vote→ `resuelta` →siguiente_turno→ `(no round)`, next lector.

## 7. Known limitations (whole-app, agreed and documented — don't rediscover)

1. **Reconnect mid-round is blind**: the REST snapshot lacks ronda stage/pregunta. The
   frontend shows a "ronda en curso…" panel with speculative recovery actions (lector:
   robar carta; host: forzar turno) that the backend safely rejects if inapplicable.
   Proper fix = backend exposing the active ronda in the snapshot.
2. **Stuck round**: if the last pending voter disconnects and no further vote ever
   arrives, the round hangs — resolution is only re-evaluated when a vote arrives, and
   the host's forced `siguiente_turno` is only allowed when the **lector** is the one
   disconnected. Backend fix required (e.g. re-evaluate resolution on voter disconnect).
3. **`unirse` answers 409 "La partida ya empezó" to existing members** once the sala is
   `en_curso` (state checked before membership). The frontend works around it on reload
   (resync + membership check).
4. **Empty deck on fresh DB** — seed preguntas before playing (UI at `/preguntas`).
5. **Min-2-players to start is enforced only by the frontend UI.**
6. Salas are single-use: `finalizada` is terminal; replay = create a new sala.

## 8. Running & testing

Environment note for sandboxed agents: this machine has **uv but no Docker** — always use
the pgserver path (`scripts/db.py`), never `docker compose`.

```bash
# Everything at once (Postgres via pgserver + migrations + backend + frontend):
./scripts/dev.sh                     # then open http://localhost:5173 (Swagger at :8000/docs)

# Full-stack E2E (starts and tears down its own stack; uses system Chrome):
./scripts/e2e.sh

# Piecemeal:
export DATABASE_URL="$(uv run --project server python scripts/db.py start)"
cd server && uv run alembic upgrade head && uv run uvicorn app.main:app --reload --port 8000
cd client && npm install && npm run dev

# Tests:
cd server && uv run pytest           # backend (~61 tests; own pgserver, no Docker needed)
cd client && npm test                # frontend unit (Vitest, ~27 tests)
cd client && npm run test:e2e        # browser E2E only (needs backend already running)
```

First run of a fresh DB: create 3–5 preguntas at `http://localhost:5173/preguntas`, then
register users in separate incognito windows (localStorage = identity), create/join a
sala, start with ≥2 players.

## 9. Conventions for agents working on this repo

- **Spanish everywhere**: user-facing strings AND code identifiers (both sides). Match
  the existing naming style (`robar_carta` / `robarCarta`, `anfitrion`, `marcador`).
- Game rules live **only** in `server/app/services/` — routers and WS dispatch stay thin.
  The frontend never trusts local role state; it derives lector/anfitrión with the same
  formulas the server uses and gracefully handles `error` events anyway.
- Backend errors are always `ErrorAplicacion` → `{"detalle": …}`; frontend REST errors
  are always `ErrorApi {detalle, status}` surfaced via toasts/inline messages.
- Backend deps/commands via `uv run …` from `server/`; frontend via `npm` from `client/`.
- Tests exist at three levels (pytest, Vitest, Playwright) — keep all green;
  `./scripts/e2e.sh` is the final proof for cross-cutting changes.

## 10. Status & pending work

- **Done** (2026-07-07): all 10 backend phases, all 5 frontend phases, verified live
  end-to-end (bugs found in verification were fixed; leftovers are §7).
- **Pending — Modo práctica**: 1 human + 2 random bots ("Modo práctica" button on the home
  screen) so the game is testable solo. Detailed plan with strict phase gates:
  [`../plans/pero-que-putas-practica.md`](../plans/pero-que-putas-practica.md). Rule: the
  executing agent implements **one phase per user request and stops** at its verification
  gate; zero changes to existing game-loop services.
