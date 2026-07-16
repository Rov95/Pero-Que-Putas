# Pero Qué Putas — Backend Context for Frontend Development

> **Purpose of this file:** complete, verified map of the backend (REST + WebSocket) for a Claude
> agent building the frontend. Everything here was extracted from the implemented code at
> `~/Desktop/Portfolio/Pero-Que-Putas/server` (branch `main`, all 10 plan phases + Modo práctica
> done, 77 tests green). When in doubt, the backend code is the source of truth — this doc
> mirrors it as of 2026-07-16.

---

## 1. Game overview (what the UI must express)

"Pero Qué Putas" is a Spanish-language party game ("¿Qué prefieres?" / would-you-rather style):

1. Players gather in a **sala** (room) identified by a 6-character invite **codigo**.
2. The **anfitrión** (host = sala creator) starts the game; players get a shuffled turn order.
3. Each round, one player is the **lector** (reader). The lector:
   - Draws a dilemma card (**pregunta**: an `enunciado` — the question text, e.g. "Si mañana
     acaba el mundo, ¿qué harías con el tiempo que te queda?" — plus its exactly two absurd
     options, Opción 1 / Opción 2),
   - Reads it aloud (physically), then makes a **secret prediction** of how the group will vote.
4. All **other** players vote simultaneously: 1 = Opción 1, 2 = Opción 2 (in person: 1 or 2 fingers).
5. Votes resolve automatically when the last expected vote arrives:
   - `todos_X` if unanimous for option X, `mayoria_X` if simple majority, `empate` if tied.
   - Prediction matching is **strict**: `mayoria_1` prediction does NOT score if the result is `todos_1`.
   - On a hit (`acierto`), the lector earns **1 point**. On `empate`, nobody ever scores.
6. The lector does **not** vote. Turn passes with `siguiente_turno` (lector or host can trigger).
7. Game ends manually: host calls `finalizar`. Points transfer to a **historic scoreboard**
   (`marcador_historico`, ties → multiple winners) and sala points reset to 0.

**All user-facing strings are Spanish.** The frontend should be Spanish-first too.

---

## 2. Conventions & base config

- Base URL (local dev): `http://localhost:8000` — REST under `/api`, WebSocket under `/ws`.
- CORS: controlled by `CORS_ORIGINS` env var on the server; **default is `http://localhost:5173`**
  (Vite's default port). Comma-separated list if more origins are needed.
- All IDs are **UUIDs** (strings in JSON). Timestamps are ISO-8601 with timezone (`creado_en`, etc.).
- **Every error response, any status code, has the same body shape:**
  ```json
  { "detalle": "<mensaje en español>" }
  ```
  This includes 422 validation errors (e.g. `{"detalle": "Dato inválido en 'username'"}`),
  409 conflicts, 404s, 403s, and 500s (`{"detalle": "Error interno del servidor"}`).
- There is **no auth**. The client identifies itself by sending its `usuario_id` in request bodies
  and in the WS query string. The frontend must persist `usuario_id` (e.g. localStorage) after
  creating a user — losing it means losing the identity (usernames are unique, re-creating fails with 409).
- Sala `codigo` alphabet: `23456789ABCDEFGHJKMNPQRSTUVWXYZ` (6 chars, no 0/O/1/I/L). Uppercase.
  The frontend should uppercase user input before sending.

### Enums (exact wire values)

| Enum | Values |
|---|---|
| `estado` (sala) | `esperando`, `en_curso`, `finalizada` |
| `estado` (ronda) | `leyendo`, `votando`, `resuelta` |
| `prediccion` | `mayoria_1`, `todos_1`, `mayoria_2`, `todos_2` |
| `resultado` | `mayoria_1`, `todos_1`, `mayoria_2`, `todos_2`, `empate` |
| `opcion` (voto) | `1`, `2` (integers) |

Spanish labels for predictions (also served by `GET /api/constantes/predicciones`):

| clave | etiqueta |
|---|---|
| `mayoria_1` | La mayoría elige la Opción 1 |
| `todos_1` | Todos eligen la Opción 1 |
| `mayoria_2` | La mayoría elige la Opción 2 |
| `todos_2` | Todos eligen la Opción 2 |

---

## 3. Shared response shapes (TypeScript)

```ts
interface Usuario {
  id: string;            // UUID
  username: string;
  creado_en: string;     // ISO datetime
}

interface Opcion {
  numero: 1 | 2;
  texto: string;
}

interface Pregunta {
  id: string;
  enunciado: string;     // the question text of the card
  creado_en: string;
  opciones: Opcion[];    // always exactly 2, ordered by numero
}

interface Jugador {
  usuario_id: string;
  username: string;
  orden_turno: number | null;  // null until the game starts
  puntos: number;
  conectado: boolean;
}

interface Sala {
  id: string;
  codigo: string;              // 6 chars
  estado: "esperando" | "en_curso" | "finalizada";
  anfitrion_id: string;
  turno_actual: number;        // raw counter, starts at 0, increments forever
  creado_en: string;
  jugadores: Jugador[];        // NOT sorted; sort by orden_turno client-side if needed
}

interface PuntoJugador {
  usuario_id: string;
  username: string;
  puntos: number;
}

interface MarcadorFinalEntrada {   // per-player result of a finished game
  usuario_id: string;
  username: string;
  puntos_finales: number;
  gano: boolean;                   // ties → multiple true
}

interface MarcadorHistoricoEntrada {  // all-time aggregate per user
  username: string;
  puntos_totales: number;
  partidas: number;
  victorias: number;
}

interface ErrorRespuesta { detalle: string; }
```

**Derived state the frontend must compute** (the backend derives it the same way, never trust local
role assumptions over server events):

```ts
// Current lector: player whose orden_turno == turno_actual % jugadores.length
const lector = sala.jugadores.find(
  j => j.orden_turno === sala.turno_actual % sala.jugadores.length
);
const soyLector   = lector?.usuario_id === miUsuarioId;
const soyAnfitrion = sala.anfitrion_id === miUsuarioId;
```

---

## 4. REST API reference

### 4.1 Salud

| | |
|---|---|
| `GET /api/salud` | → `200 {"estado": "ok"}` — health check |

### 4.2 Usuarios

**`POST /api/usuarios`** — create user (first thing the app does)
- Body: `{ "username": string }` — 3–30 chars, **no whitespace** (regex `^\S+$`)
- `201` → `Usuario`
- `409` `"Ese nombre ya está en uso"` — uniqueness is **case-insensitive and global**
- `422` on invalid username

**`GET /api/usuarios/{usuario_id}`**
- `200` → `Usuario` · `404` `"Usuario no encontrado"`

### 4.3 Preguntas (card deck CRUD — admin/content screens)

**`GET /api/preguntas?desplazamiento=0&limite=20`** — paginated list
- Query: `desplazamiento` ≥ 0 (offset, default 0); `limite` 1–100 (default 20)
- `200` → `Pregunta[]` (each embeds both `opciones`), ordered by `creado_en`

**`POST /api/preguntas`** — create card (enunciado + its 2 options, atomic)
- Body: `{ "enunciado": string, "opcion_1": string, "opcion_2": string }` (all non-empty)
- `201` → `Pregunta`

**`GET /api/preguntas/{id}`** → `200 Pregunta` · `404 "Pregunta no encontrada"`

**`PUT /api/preguntas/{id}`** — full-card update (enunciado + both option texts)
- Body: `{ "enunciado": string, "opcion_1": string, "opcion_2": string }` (all non-empty)
- `200` → `Pregunta` · `404 "Pregunta no encontrada"` · `422`
- This is what the frontend's edit flow uses.

**`GET /api/preguntas/{id}/opciones`** → `200 { "opcion_1": string, "opcion_2": string }`
(options-only sub-resource; no UI uses it)

**`PUT /api/preguntas/{id}/opciones`** — replace both option texts (does NOT touch `enunciado`)
- Body: `{ "opcion_1": string, "opcion_2": string }`
- `200` → `{ "opcion_1", "opcion_2" }` (no UI uses it — superseded by `PUT /api/preguntas/{id}`)

**`DELETE /api/preguntas/{id}`** → `204` · `404`
- If the card was **never played**, the row is hard-deleted (cascades to opciones).
- If any ronda references it (`rondas.pregunta_id` has no `ON DELETE`), it is
  **soft-deleted** instead: `preguntas.eliminada = true`. Same `204`; the card
  disappears from `GET /api/preguntas`, `GET/PUT /{id}` return `404`, and it is
  never drawn again — but round history and any active round stay intact.
  (Before 2026-07-16 this case incorrectly surfaced as a `409` FK conflict.)

### 4.4 Constantes

**`GET /api/constantes/predicciones`**
- `200` → `[{ "clave": string, "etiqueta": string }]` — the 4 predictions in §2.
  Use this to render the lector's prediction picker (don't hardcode labels).

### 4.5 Salas

**`POST /api/salas`** — create room; creator becomes anfitrión AND is auto-joined as a player
- Body: `{ "usuario_id": string }`
- `201` → `Sala` (grab `codigo` to share/join) · `404 "Usuario no encontrado"`

**`POST /api/salas/practica`** — Modo práctica: create a room with the caller as anfitrión
**plus 2 bots** already created and joined (see §5.6). The server launches one in-process WS
client task per bot right after responding, so the lobby reaches "3 conectados" by itself
within a couple of seconds — no second human needed to pass the frontend's min-2 gate.
- Body: `{ "usuario_id": string }`
- `201` → `Sala` (3 jugadores: the human + 2 `Bot-<Apodo>-<sufijo>`; the bots may still show
  `conectado=false` in this response — they connect asynchronously moments later and the
  usual `jugador_unido` events arrive over the WS)
- `404 "Usuario no encontrado"` · `409 "No hay preguntas disponibles. Crea algunas en la
  pantalla de preguntas antes de practicar."` (checked upfront — a practice game can't draw
  cards from an empty deck either)

**`POST /api/salas/{codigo}/unirse`** — join room
- Body: `{ "usuario_id": string }`
- `200` → `Sala` (updated player list). **Idempotent** — joining twice is a no-op success.
- `404 "Sala no encontrada"` · `409 "La partida ya empezó"` · `404 "Usuario no encontrado"`

**`GET /api/salas/{codigo}`** — full room state. **This is also the reconnection endpoint**:
after a WS drop, re-fetch this to resync, then reopen the WS.
- `200` → `Sala` · `404 "Sala no encontrada"`

**`POST /api/salas/{codigo}/iniciar`** — host starts the game
- Body: `{ "usuario_id": string }` (must be anfitrión)
- Assigns shuffled `orden_turno` to every player, sets `estado=en_curso`, `turno_actual=0`.
- Side effect: broadcasts WS `partida_iniciada` then `turno_actual` to all connected sockets.
- `200` → `Sala` · `403 "Solo el anfitrión puede iniciar la partida"` · `409 "La partida ya empezó"`

**`POST /api/salas/{codigo}/finalizar`** — host ends the game
- Body: `{ "usuario_id": string }` (must be anfitrión; sala must be `en_curso`)
- Single transaction: writes one `marcador_historico` row per player (`gano=true` for max score,
  ties included), resets everyone's `puntos` to 0, sets `estado=finalizada`.
- Side effect: broadcasts WS `partida_finalizada`.
- `200` → `{ "sala": Sala, "marcador_final": MarcadorFinalEntrada[] }`
- `403 "Solo el anfitrión puede finalizar la partida"` · `409 "La partida no está en curso"`

### 4.6 Puntos + marcador

**`GET /api/salas/{codigo}/puntos`** → `200 PuntoJugador[]` — active-game points, all players

**`PUT /api/salas/{codigo}/puntos/{usuario_id}`** — manual score correction
- Body: `{ "puntos": number }`
- `200` → `PuntoJugador` · `404 "Ese usuario no pertenece a esta sala"` · `404 "Sala no encontrada"`

**`DELETE /api/salas/{codigo}/puntos`** → `204` — reset all sala points to 0

**`GET /api/marcador`** — historic all-time scoreboard
- Optional query: `?usuario_id=<uuid>` filters to one user
- `200` → `MarcadorHistoricoEntrada[]`, sorted by `puntos_totales` descending
- Only users who have finished ≥1 game appear.

---

## 5. WebSocket protocol

### 5.1 Connection

```
WS ws://localhost:8000/ws/salas/{codigo}?usuario_id={uuid}
```

- Connect **after** joining the sala via REST (membership is validated on connect).
- The server accepts the socket first, then validates. On failure it **closes with code 4003**
  and a Spanish reason: `"Sala no encontrada"` or `"No perteneces a esta sala"`.
  Frontend: treat close code 4003 as "kick back to join screen with the reason".
- On successful connect the server sets your `conectado=true` and broadcasts `jugador_unido`
  to **everyone else** (you do NOT receive your own join event).
- On disconnect (any reason) the server sets `conectado=false` and broadcasts `jugador_salio`
  to the remaining sockets.
- `conectado` matters for gameplay: **round resolution only waits for connected voters**
  (a disconnected player never blocks a round).

### 5.2 Message envelope (both directions)

```json
{ "evento": "<nombre>", "datos": { ... } }
```

`datos` may be `{}` but the key should be present on sends (server tolerates `null`/missing).

### 5.3 Client → Server events

| evento | datos | Who may send | Errors (sent back as `error` event) |
|---|---|---|---|
| `robar_carta` | `{}` | current lector only | 403 not lector · 409 partida not en_curso · 409 round already active · 409 `"No quedan preguntas disponibles"` (deck exhausted for this sala — no repeats) |
| `prediccion_secreta` | `{ "prediccion": "mayoria_1" \| "todos_1" \| "mayoria_2" \| "todos_2" }` | current lector only | 403 not lector · 409 no round awaiting prediction · 400 `"Predicción inválida"` |
| `voto` | `{ "opcion": 1 \| 2 }` | any player EXCEPT the lector | 403 `"El lector no vota"` · 409 no round in voting stage · 409 `"Ya votaste en esta ronda"` · 400 `"Voto inválido"` |
| `siguiente_turno` | `{}` | current lector OR anfitrión | 403 otherwise · 409 `"Termina la ronda actual antes de continuar"` (unless the current lector is disconnected — then the host CAN force it, abandoning the stuck round) |
| anything else | — | — | 400 `"Evento desconocido: <nombre>"` |

**Error delivery:** business-rule violations never close the socket. The server replies with an
`error` event **only to the offending socket**:

```json
{ "evento": "error", "datos": { "detalle": "Ya votaste en esta ronda" } }
```

### 5.4 Server → Client events (broadcast to the whole sala unless noted)

| evento | datos payload | When |
|---|---|---|
| `jugador_unido` | `{ "usuario_id", "username" }` | someone connects (not sent to that someone) |
| `jugador_salio` | `{ "usuario_id", "username" }` | someone disconnects |
| `partida_iniciada` | `{ "orden": [{ "usuario_id", "username", "orden_turno" }], "lector": { "usuario_id", "username" } }` | host called REST `iniciar`; `orden` is sorted by `orden_turno` |
| `turno_actual` | `{ "numero": int, "lector": { "usuario_id", "username" } }` | right after `partida_iniciada`, and after every accepted `siguiente_turno` |
| `carta_robada` | `{ "ronda_id": uuid, "pregunta": { "id", "enunciado", "opcion_1", "opcion_2" } }` | lector drew a card; UI shows the question + two options to everyone |
| `prediccion_registrada` | `{ "lector_id": uuid }` | lector locked a prediction. **Never contains the prediction itself** — voting UI opens for non-lectors |
| `voto_registrado` | `{ "votos_recibidos": int, "votos_esperados": int }` | each accepted vote. **Never says who voted what.** Show progress (e.g. 2/3) |
| `resultado_ronda` | `{ "votos": [{ "usuario_id", "username", "opcion" }], "resultado", "prediccion", "acierto": bool, "puntos_lector": int }` | fires automatically right after the `voto_registrado` of the final expected vote — the big reveal: every vote, the result, the secret prediction, hit/miss, lector's new total |
| `partida_finalizada` | `{ "marcador_final": MarcadorFinalEntrada[] }` | host called REST `finalizar` |
| `error` | `{ "detalle": string }` | only to the socket that sent a bad event |

**Secrecy guarantees the UI can rely on (and must not break):** individual votes and the lector's
prediction are never observable before `resultado_ronda` — not via WS events and not via any REST
endpoint. Don't design UI that expects them earlier.

### 5.5 Round state machine (drives the game screen)

```
(no round)                     lector sends robar_carta
  └─> ronda "leyendo"     ──── everyone gets carta_robada; lector sees prediction picker
        lector sends prediccion_secreta
  └─> ronda "votando"     ──── everyone gets prediccion_registrada; non-lectors see vote buttons
        each non-lector (connected) sends voto → voto_registrado (n/m)
        last expected vote arrives → server auto-resolves
  └─> ronda "resuelta"    ──── everyone gets resultado_ronda; show reveal + scores
        lector or host sends siguiente_turno → turno_actual (new lector)
  └─> back to (no round) for the next lector
```

`votos_esperados` = number of players with `conectado=true` excluding the lector, evaluated
per vote — it can change mid-round if someone disconnects.

### 5.6 Bots (Modo práctica) — what they look like on the wire

The 2 bots created by `POST /api/salas/practica` (§4.5) are **indistinguishable from human
players** to any client: ordinary `usuarios` rows (username `Bot-<Apodo>-<sufijo>`, e.g.
`Bot-Luna-7XK2`), real WebSocket connections (in-process tasks inside the backend,
`server/app/bots/`), ordinary `jugador_unido` / `voto_registrado` / `resultado_ronda`
events, ordinary rows in the podium and in `GET /api/marcador` (accepted trade-off: the
historic scoreboard does not filter them). The frontend needs — and has — zero
special-casing.

Behavior (server-side, `app/bots/jugador.py`; delays configurable via server env vars):

- Every action is preceded by a random delay in `BOTS_RETRASO_MIN_MS`–`BOTS_RETRASO_MAX_MS`
  (defaults 800–2500 ms) so the pacing feels human.
- As votante: votes 1 or 2 uniformly at random.
- As lector: `robar_carta` → uniformly random `prediccion_secreta` → after
  `resultado_ronda`, sends `siguiente_turno` after `BOTS_RETRASO_SIGUIENTE_TURNO_MS`
  (default 4000 ms) plus jitter — the human gets ~4–6.5 s to read the reveal before the
  round auto-advances. UI must not assume the human drives every turn change.
- Terminates cleanly on `partida_finalizada`, on its socket closing, or after
  `BOTS_VIDA_MAXIMA_SEGUNDOS` (default 1800 s — abandoned practice rooms clean themselves
  up; after that the bots just count as disconnected players).

---

## 6. Canonical client flows

### 6.1 Onboarding
1. `POST /api/usuarios {username}` → store `usuario_id` locally (localStorage).
2. On 409, prompt for a different name (or if the stored id exists, `GET /api/usuarios/{id}` to restore session).

### 6.2 Create / join lobby
1. Host: `POST /api/salas {usuario_id}` → show `codigo` big on screen.
2. Guests: `POST /api/salas/{codigo}/unirse {usuario_id}`.
3. Everyone: open WS `/ws/salas/{codigo}?usuario_id=...`.
4. Render lobby from `Sala.jugadores`; live-update with `jugador_unido` / `jugador_salio`.
5. Host presses start → `POST /api/salas/{codigo}/iniciar` → everyone receives
   `partida_iniciada` + `turno_actual` over WS (the REST response is only relevant to the host).

### 6.3 Round loop
Follow §5.5. All in-game actions are **WS events, not REST**.

### 6.4 Ending
1. Host: `POST /api/salas/{codigo}/finalizar` → all clients get `partida_finalizada` with the podium.
2. Show final scores (`gano` flags — possibly several winners on ties).
3. Optional: `GET /api/marcador` for the all-time leaderboard screen.

### 6.5 Reconnection (must-have)
On WS close (non-4003) or app resume:
1. `GET /api/salas/{codigo}` → rebuild full state (estado, jugadores, puntos, turno_actual → derive lector).
2. Reopen the WS with the same `usuario_id`.
3. Limitation to design around: the REST snapshot does **not** include the active ronda's stage
   (leyendo/votando) or the current pregunta text. After reconnecting mid-round, the client won't
   know the card/stage until the next event arrives (`resultado_ronda`, `turno_actual`, …).
   Simplest UX: show a "ronda en curso…" waiting panel until the next event, or have the lector/host
   use `siguiente_turno` (host can force it if the lector dropped).

---

## 7. Edge cases & rules the frontend must respect

- **Never trust local role state** — the backend re-validates lector/anfitrión on every action and
  answers with an `error` event; the UI should still hide invalid actions (lector sees no vote
  buttons, non-hosts see no iniciar/finalizar) but must handle `error` events gracefully anyway.
- **Tie (`empate`)**: possible with an even number of voters. `resultado_ronda.acierto` is always
  false; show "¡Empate! Nadie puntúa".
- **Deck exhaustion**: `robar_carta` fails with `"No quedan preguntas disponibles"` once every
  pregunta has been used in that sala (no repeats per sala). Soft-deleted preguntas
  (`eliminada = true`, see `DELETE /api/preguntas/{id}`) are excluded from the draw too.
  The UI should surface this and suggest finishing the game (or adding preguntas).
- **Duplicate join is safe**; duplicate vote is a 409 `error` event.
- **`turno_actual` is a raw counter** (can exceed player count) — always use modulo to find the lector.
- **`estado=finalizada` salas are dead**: you can still `GET` them, but no game actions work; you
  can't re-iniciar (returns `409 "La partida ya empezó"`). New game = new sala.
- **Sala codes**: server generates them without 0/O/1/I/L; normalize user input to uppercase.
- **Host disconnection is not special** — the sala continues; the host can reconnect and still is
  anfitrión. Only lector disconnection has a special rule (host may force `siguiente_turno`).
- **422 responses** come from body validation (shape `{"detalle": "Dato inválido en '<campo>'"}`).

---

## 8. Running the backend locally (for frontend dev)

From `~/Desktop/Portfolio/Pero-Que-Putas/server`:

```bash
# 1. Postgres (real machine with Docker):
docker compose up -d          # postgres:16 on localhost:5432, creds pero_que_putas/pero_que_putas

# 2. Env — .env already exists (copy of .env.example):
#    DATABASE_URL=postgresql+asyncpg://pero_que_putas:pero_que_putas@localhost:5432/pero_que_putas
#    CORS_ORIGINS=http://localhost:5173     <-- add your frontend origin here if different

# 3. Migrations + run (uv-managed project, Python 3.12):
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

- Interactive API docs at `http://localhost:8000/docs` (FastAPI/Swagger — useful to poke endpoints).
- Tests (`uv run pytest`) need no Docker — they spin up an embedded Postgres via `pgserver`.
- **Seed data caveat: the DB starts with zero preguntas.** The game cannot play a round until at
  least one pregunta exists — create some via `POST /api/preguntas` (the frontend should include a
  card-creation screen, or seed a few during development).

## 9. Backend layout (if you need to read the source)

```
server/app/
├── main.py               # create_app(), router registration, exception handlers
├── config.py             # Settings: DATABASE_URL, CORS_ORIGINS (.env)
├── constants.py          # PrediccionEnum, ResultadoEnum, Estado*Enum + Spanish labels
├── errores.py            # ErrorAplicacion(detalle, status_code)
├── manejadores.py        # global exception handlers → {"detalle"} bodies
├── models/               # SQLAlchemy: usuario, pregunta(+Opcion), sala(+SalaJugador),
│                         #   ronda(+Voto), marcador
├── schemas/              # Pydantic request/response models (mirror §3)
├── routers/              # usuarios, preguntas, constantes, salas, puntos (thin handlers)
├── services/             # ALL game rules: salas.py, juego.py, preguntas.py, usuarios.py, marcador.py
├── websocket/
│   ├── manager.py        # in-memory {codigo: {usuario_id: WebSocket}}
│   ├── router.py         # WS endpoint + event dispatch
│   └── eventos.py        # event names + payload builders (exact wire shapes)
└── bots/                 # Modo práctica (§5.6): fabrica.py (crea usuarios Bot-*),
                          #   jugador.py (WS client loop), registro.py (task registry per sala)
```

## 10. Suggested frontend surface (minimum screens)

1. **Registro** — pick username (handle 409/422 inline).
2. **Inicio** — create sala / join by codigo; link to marcador histórico and preguntas admin.
3. **Lobby** — codigo displayed big, live player list (conectado dots), host-only "Iniciar" button.
4. **Juego** — the round loop UI (three sub-states per §5.5, role-dependent: lector vs votante),
   scoreboard sidebar, vote progress (`votos_recibidos/votos_esperados`), reveal animation on
   `resultado_ronda`, host-only "Finalizar" + lector/host "Siguiente turno".
5. **Podio** — `partida_finalizada` results (multiple winners on tie).
6. **Marcador histórico** — `GET /api/marcador` table.
7. **Preguntas (admin)** — CRUD for cards (needed since the deck starts empty).
