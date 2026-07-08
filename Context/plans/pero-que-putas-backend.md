# Plan: Backend "Pero Qué Putas" (¿Qué prefieres?)

> **Implementation plan for Claude Code.** Repo: `~/Desktop/Portfolio/Pero-Que-Putas/server`
> Work through the phases in order; tick checkboxes as tasks complete. Each phase
> ends with a verification gate — do not start the next phase until it passes.
> All user-facing strings (errors, labels, event payloads) are in **Spanish**.
> Code identifiers use Spanish domain vocabulary (sala, lector, ronda, marcador)
> for consistency with the game's domain.

**Status:** All 10 phases complete, full pytest suite green (61 tests) · **Last updated:** 2026-07-07

---

## 0. Game rules (source of truth)

1. Party game in Spanish, played in **salas** (rooms) with a unique invite code; many salas run concurrently.
2. Each turn one player (the **lector**) draws a dilemma card with two absurd options (Opción 1 / Opción 2) and reads it aloud.
3. The lector makes a **secret prediction** of the group vote — one of 4 fixed values: `mayoria_1`, `todos_1`, `mayoria_2`, `todos_2`.
4. All other players vote simultaneously (1 finger = Opción 1, 2 fingers = Opción 2).
5. If the prediction matches the real outcome, the lector earns **1 point** (keeps the card).
6. Game end: highest points wins; points transfer to a **historic scoreboard** and reset for the next game.

## 1. Decisions locked (defaults chosen so development never blocks)

These were ambiguities; defaults are chosen and flagged. **Ask the user to confirm
the ⚠ ones before Phase 8 (game loop); everything before that is unaffected.**

| # | Decision | Default | Notes |
|---|---|---|---|
| 1 | ✅ Prediction enum meaning | `mayoria_1, todos_1, mayoria_2, todos_2` = majority/unanimity × option 1/2 | Confirmed with user 2026-07-07 |
| 2 | ✅ Does `todos_X` also satisfy `mayoria_X`? | **No — strict match.** Predicting `mayoria_1` when result is `todos_1` does NOT score | Confirmed with user 2026-07-07 |
| 3 | ✅ Tie in votes (even voter count) | `resultado = empate`, nobody scores | Confirmed with user 2026-07-07 |
| 4 | Game end trigger | Manual: host calls `POST /finalizar` | Round-count / point-target easy to add later as sala config |
| 5 | Does the lector vote? | **No** (standard for the genre) | Affects `votos_esperados` |
| 6 | Username uniqueness | **Global** (case-insensitive), not per-sala | Required for a meaningful historic scoreboard + future auth identity |
| 7 | Disconnect mid-vote | Resolution waits only for players with `conectado = true` | A disconnected player never blocks the round |
| 8 | Auth | None now; services take `usuario_id` as a parameter so a future `Depends(obtener_usuario_actual)` slots in with zero refactor | Add `email`/`hash_password` columns via migration later |

## 2. Stack (fixed)

- **FastAPI** + Uvicorn, **Python 3.12+**, managed with `uv` (fall back to pip/venv if uv unavailable)
- **PostgreSQL 16** via **docker-compose** for local dev
- **SQLAlchemy 2.0 async** + `asyncpg`, **Alembic** migrations
- **Pydantic v2** + `pydantic-settings` (`.env`: `DATABASE_URL`, `CORS_ORIGINS`)
- Tests: **pytest** + `pytest-asyncio` + `httpx` (REST) + Starlette `TestClient` (WebSocket)
- WebSockets: native FastAPI; in-memory `ConexionesManager`. **DB is the single
  source of truth for game state** — the manager only maps sockets. Swap the
  broadcast for Redis pub/sub later if multi-worker is ever needed; isolate that
  in `websocket/manager.py` so nothing else changes.

## 3. Data model (create in this exact shape, one initial Alembic migration)

All PKs are `UUID` (server-generated). Timestamps are `TIMESTAMPTZ`.

```
usuarios
  id UUID PK
  username VARCHAR(30) NOT NULL — UNIQUE case-insensitive (CITEXT or unique index on lower(username))
  creado_en

preguntas
  id UUID PK
  creado_en

opciones                      -- exactly 2 per pregunta, never shared between preguntas
  id UUID PK
  pregunta_id FK → preguntas ON DELETE CASCADE
  numero SMALLINT CHECK (numero IN (1,2))
  texto TEXT NOT NULL
  UNIQUE (pregunta_id, numero)

salas
  id UUID PK
  codigo VARCHAR(6) UNIQUE    -- alphanumeric, exclude ambiguous chars (0/O, 1/I/L); retry on collision
  estado ENUM(esperando, en_curso, finalizada)
  anfitrion_id FK → usuarios
  turno_actual INT DEFAULT 0
  creado_en

sala_jugadores
  id UUID PK
  sala_id FK → salas
  usuario_id FK → usuarios
  orden_turno SMALLINT        -- assigned at game start; lector = orden_turno == turno_actual % n_jugadores
  puntos INT DEFAULT 0        -- ACTIVE-game score; reset on finalizar
  conectado BOOLEAN DEFAULT false
  unido_en
  UNIQUE (sala_id, usuario_id)

rondas
  id UUID PK
  sala_id FK → salas
  numero INT                  -- sequential within sala
  pregunta_id FK → preguntas  -- random draw excludes preguntas already in rondas for this sala (no repeats)
  lector_id FK → usuarios
  prediccion ENUM(mayoria_1, todos_1, mayoria_2, todos_2) NULL  -- SECRET until resolution
  estado ENUM(leyendo, votando, resuelta)
  resultado ENUM(mayoria_1, todos_1, mayoria_2, todos_2, empate) NULL
  acierto BOOLEAN NULL

votos
  id UUID PK
  ronda_id FK → rondas
  usuario_id FK → usuarios
  opcion SMALLINT CHECK (opcion IN (1,2))
  UNIQUE (ronda_id, usuario_id)

marcador_historico            -- one row per player per finished game, written transactionally
  id UUID PK
  usuario_id FK → usuarios
  sala_id FK → salas
  puntos_finales INT
  gano BOOLEAN                -- true for max score (ties → multiple winners)
  finalizada_en
```

Prediction constants are **not a table**: Python `PrediccionEnum` (str) in
`app/constants.py` with Spanish labels, mirrored as a PG enum. Labels:
`mayoria_1` → "La mayoría elige la Opción 1", `todos_1` → "Todos eligen la
Opción 1", `mayoria_2` → "La mayoría elige la Opción 2", `todos_2` → "Todos
eligen la Opción 2".

Indexes: `salas.codigo`, `rondas(sala_id)`, `votos(ronda_id)`, `marcador_historico(usuario_id)`.

## 4. API surface

Prefix `/api`. Error body always `{"detalle": "<mensaje en español>"}`.

### REST

| Método | Ruta | Notas |
|---|---|---|
| POST | `/api/usuarios` | `{username}` → 201; 409 "Ese nombre ya está en uso" |
| GET | `/api/usuarios/{id}` | |
| GET | `/api/preguntas` | list with embedded `opciones`; paginated |
| POST | `/api/preguntas` | `{opcion_1, opcion_2}` → creates pregunta + 2 opciones **atomically** |
| GET | `/api/preguntas/{id}` | |
| GET | `/api/preguntas/{id}/opciones` | getter |
| PUT | `/api/preguntas/{id}/opciones` | setter: `{opcion_1, opcion_2}` replaces both texts |
| DELETE | `/api/preguntas/{id}` | CASCADE removes opciones |
| GET | `/api/constantes/predicciones` | `[{clave, etiqueta}]`, the 4 constants |
| POST | `/api/salas` | `{usuario_id}` → creator is anfitrión, returns `codigo` |
| POST | `/api/salas/{codigo}/unirse` | 404 "Sala no encontrada"; 409 "La partida ya empezó" |
| GET | `/api/salas/{codigo}` | full state — also the reconnection endpoint |
| POST | `/api/salas/{codigo}/iniciar` | host only (403 otherwise); assigns orden_turno, estado=en_curso |
| POST | `/api/salas/{codigo}/finalizar` | host only; transactional transfer to marcador_historico + reset puntos + estado=finalizada |
| GET | `/api/salas/{codigo}/puntos` | active-game points, all players |
| PUT | `/api/salas/{codigo}/puntos/{usuario_id}` | manual correction setter |
| DELETE | `/api/salas/{codigo}/puntos` | reset all sala points to 0 |
| GET | `/api/marcador` | historic aggregate: `[{username, puntos_totales, partidas, victorias}]`; optional `?usuario_id` |

Split rule: REST = CRUD + queryable state; WebSocket = only the live game flow.

### WebSocket — `WS /ws/salas/{codigo}?usuario_id={uuid}`

Validate membership on connect; reject with close code 4003 + Spanish reason.
Message envelope both directions: `{"evento": "...", "datos": {...}}`.

Client → Server: `robar_carta` (lector only) · `prediccion_secreta {prediccion}`
(lector only) · `voto {opcion}` (non-lector only) · `siguiente_turno` (lector or host).

Server → Client (broadcast to sala): `jugador_unido` / `jugador_salio` ·
`partida_iniciada {orden, lector}` · `turno_actual {numero, lector}` ·
`carta_robada {ronda_id, pregunta}` · `prediccion_registrada {lector_id}`
(**never** the prediction content) · `voto_registrado {votos_recibidos, votos_esperados}`
(**never** which option) · `resultado_ronda {votos, resultado, prediccion, acierto, puntos_lector}`
(everything revealed at once) · `partida_finalizada {marcador_final}` ·
`error {detalle}` (only to the offending socket).

Resolution logic (server-side, triggered automatically when the last expected vote lands):
count votes → `todos_X` if unanimous, `mayoria_X` if simple majority, `empate` if
equal → `acierto = (prediccion == resultado)` strict → if acierto, lector's
`puntos += 1` → persist ronda → broadcast `resultado_ronda`.

## 5. Folder structure

```
server/
├── app/
│   ├── main.py               # create_app(), include routers, exception handlers
│   ├── config.py             # Settings (pydantic-settings)
│   ├── database.py           # async engine, session factory, Base
│   ├── constants.py          # PrediccionEnum + Spanish labels
│   ├── models/               # usuario.py, pregunta.py (+Opcion), sala.py (+SalaJugador),
│   │                         #   ronda.py (+Voto), marcador.py
│   ├── schemas/              # Pydantic mirrors + WS payload models
│   ├── routers/              # usuarios.py, preguntas.py, constantes.py, salas.py, puntos.py
│   ├── services/             # ALL game rules live here (thin handlers):
│   │   ├── salas.py          #   crear/unirse/iniciar/finalizar
│   │   └── juego.py          #   robar carta, predicción, votos, resolución, puntuación
│   └── websocket/
│       ├── manager.py        # ConexionesManager: {codigo: {usuario_id: WebSocket}}
│       ├── router.py         # WS endpoint + event dispatch
│       └── eventos.py        # event names + payload builders
├── alembic/
├── tests/
├── docker-compose.yml        # postgres:16
├── pyproject.toml
└── .env.example
```

## 6. Phases

### Phase 1 — Foundation
- [x] `pyproject.toml`: fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, pytest, pytest-asyncio, httpx
- [x] `docker-compose.yml` with postgres:16; `.env.example` + `.env`
- [x] `config.py`, `database.py`, `main.py` with `GET /api/salud` → `{"estado": "ok"}`
- **Gate:** `docker compose up -d` + `uvicorn app.main:app` boots; `curl /api/salud` returns ok. ✅ PASSED

### Phase 2 — Models + initial migration
- [x] All SQLAlchemy models from §3; `constants.py` with `PrediccionEnum`
- [x] Alembic init (async template) + single initial migration
- **Gate:** `alembic upgrade head` clean on fresh DB; `\d` shows all constraints (CHECKs, UNIQUEs, enums). ✅ PASSED

### Phase 3 — Usuarios
- [x] POST/GET endpoints; username 3–30 chars, no spaces, case-insensitive uniqueness → 409 in Spanish
- **Gate:** pytest for create/duplicate/get; duplicate differing only in case → 409. ✅ PASSED

### Phase 4 — Preguntas + opciones
- [x] Service: atomic create (pregunta + exactly 2 opciones in one transaction)
- [x] All 6 endpoints from §4 incl. opciones getter/setter
- **Gate:** pytest: create, list embeds both opciones, PUT replaces texts, DELETE cascades. ✅ PASSED

### Phase 5 — Constantes
- [x] `GET /api/constantes/predicciones` returning the 4 `{clave, etiqueta}` pairs
- **Gate:** response matches §3 labels exactly. ✅ PASSED

### Phase 6 — Salas (REST)
- [x] Code generator (6 chars, no ambiguous glyphs, collision retry)
- [x] crear / unirse / consultar / iniciar with state validation (409 if en_curso, 403 non-host iniciar)
- **Gate:** pytest covering happy path + each error case. ✅ PASSED

### Phase 7 — WebSocket base
- [x] `ConexionesManager` (conectar/desconectar/broadcast); membership check on connect (4003)
- [x] `jugador_unido`/`jugador_salio` events; `conectado` flag persisted
- **Gate:** WS test: two clients in one sala see each other join/leave; client in sala B sees nothing. ✅ PASSED

### Phase 8 — Game loop ⚠ (confirm decisions 1–3 in §1 with the user first)
- [x] `services/juego.py`: robar_carta (random, no repeats per sala) → prediccion_secreta → voto → auto-resolution per §4
- [x] Turn rotation via `siguiente_turno`; role enforcement (only lector draws/predicts, lector cannot vote, one vote per player)
- **Gate:** pytest on resolution service: unanimity / majority / empate × prediction hit/miss (8+ cases). WS test: full round with 3 clients, secrecy verified (prediction and individual votes never leak before `resultado_ronda`). ✅ PASSED

### Phase 9 — Puntos + marcador
- [x] GET/PUT/DELETE puntos endpoints
- [x] `finalizar`: single transaction (insert marcador rows, mark gano incl. ties, reset puntos, estado=finalizada) + `partida_finalizada` broadcast
- [x] `GET /api/marcador` aggregate
- **Gate:** pytest: finalizar is all-or-nothing (force a failure mid-transaction, assert rollback); tie produces two `gano=true`. ✅ PASSED

### Phase 10 — Robustness + E2E
- [x] Global exception handlers → `{"detalle"}` Spanish (validation errors translated, IntegrityError → 409)
- [x] Reconnection flow (client re-fetches `GET /api/salas/{codigo}`, re-subscribes); lector disconnect mid-round handled (decision #7)
- [x] E2E test: full 3-player game over WS, start to marcador_historico
- **Gate:** full pytest suite green; E2E passes. ✅ PASSED (61/61 tests)

## 7. Working agreements (for me, the implementer)

- Handlers stay thin; every game rule lives in `services/` so it's testable without HTTP/WS.
- Never trust the client for role checks (lector/anfitrión) — always re-derive from DB.
- Every state-changing service validates the sala/ronda estado first; violations raise a domain error mapped to 409/403 with a Spanish message.
- Run the phase gate before moving on; if a gate fails, fix before proceeding.
- Commit at the end of each phase with a message naming the phase.
