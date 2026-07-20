# Pero Qué Putas — Frontend Context

> **Purpose of this file:** complete, verified map of the frontend at
> `~/Desktop/Portfolio/Pero-Que-Putas/client` so a Claude agent can work on it **without
> re-reading the whole project**. Mirrors the implemented code on branch `main` as of
> 2026-07-17. When in doubt, the code is the source of truth.
>
> Companion docs (same folder): [`backend-api.md`](backend-api.md) — the REST/WS contract the
> frontend consumes; [`app-overview.md`](app-overview.md) — whole-app map.

---

## 1. What it is

Mobile-first Spanish-language web client for the party game "Pero Qué Putas"
(question cards — an `enunciado` plus 2 options — with secret predictions; game rules in
`app-overview.md` §1). Players
register a username (or log back in by name — no passwords; the server issues a bearer
session token), create/join a **sala** by 6-char code, and play rounds in real time
over a WebSocket. **All UI text AND all code identifiers are in Spanish** — components,
slices, actions, variables (`robarCarta`, `soyLector`, `anfitrion`). Keep new code in the
same convention.

## 2. Stack

| Concern | Choice |
|---|---|
| Framework | React 19 + TypeScript (strict), function components + hooks only |
| Build | Vite 8, dev server on **:5173 (strictPort)** |
| State | Redux Toolkit 2 (slices + createAsyncThunk) + custom WS middleware |
| Routing | react-router-dom 7, `createBrowserRouter` |
| Styles | Tailwind CSS v4 (`@theme` design tokens in `src/estilos/index.css`, dark-only) |
| Unit tests | Vitest + Testing Library, jsdom (`npm test`) |
| E2E | Playwright, **system Chrome** (`channel: 'chrome'`, no browser download), `npm run test:e2e` |
| Env | `.env` → `VITE_API_URL` (default `http://localhost:8000`) |

npm scripts: `dev`, `build` (tsc -b + vite build), `preview`, `lint`, `format`, `test`,
`test:watch`, `test:e2e`.

## 3. Directory map (`client/src/`)

```
main.tsx                    # ReactDOM root + Redux <Provider>
App.tsx                     # restores session, then mounts router; global <Notificaciones/>
api/                        # thin typed REST wrappers (one module per resource)
  clienteHttp.ts            # fetch wrapper (adds Authorization: Bearer) + urlWsSala() +
                            #   establecerManejador401(); all errors → ErrorApi
  usuariosApi.ts sesionesApi.ts salasApi.ts preguntasApi.ts marcadorApi.ts constantesApi.ts
ws/
  clienteWs.ts              # ConexionSala class — owns the raw WebSocket
  wsMiddleware.ts           # Redux middleware: send intents, dispatch server events, reconnect
store/
  index.ts                  # rootReducer + store (wsMiddleware concat'd); RootState, AppDispatch
  hooks.ts                  # useAppDispatch / useAppSelector (typed)
  slices/                   # sesion, sala, puntajes, constantes, ui
seleccionadores/juego.ts    # derived game state (lector, roles, sorted players…)
tipos/
  modelos.ts                # REST models (mirror of backend-api.md §3)
  eventosWs.ts              # WS envelopes, discriminated unions EventoCliente/EventoServidor
  api.ts                    # request bodies, ErrorApi, detalleDeError()
paginas/
  inicio/                   # PaginaInicio + FormularioRegistro/FormularioUnirse/BotonCrearSala/BotonPractica
  sala/                     # PaginaSala + VistaLobby/VistaJuego/VistaPodio + useConexionSala
  sala/juego/               # PanelLector, PanelVotante, PanelResultado, PanelRondaDesconocida,
                            #   SelectorPrediccion, ProgresoVotos, MarcadorLateral
  marcador/PaginaMarcador.tsx
  preguntas/                # PaginaPreguntas + FormularioPregunta + TarjetaPreguntaAdmin
componentes/                # Boton, CampoTexto, FichaJugador, TarjetaDilema, Notificaciones,
                            #   PantallaCarga, EstadoVacio
utilidades/                 # almacenamiento (localStorage), codigoSala, useEnfoqueAlMontar
estilos/index.css           # Tailwind v4 @theme tokens + keyframes (aparecer, revelar)
tests/                      # Vitest: sesionSlice, salaSlice, seleccionadores/juego, wsMiddleware
```

E2E lives outside src (excluded from Vitest via `vite.config.ts`):
`client/e2e/juego-completo.spec.ts` (3 browser contexts play a full game),
`client/e2e/practica.spec.ts` (Modo práctica: 1 browser + 2 server bots to the podium) and
`client/e2e/sesion.spec.ts` (logout: token revoked + storage wiped, then login by name).

## 4. Routes & screens

| Route | Component | What it does |
|---|---|---|
| `/` | `PaginaInicio` | Registro/login form (if no session) OR: greeting, "Volver a la sala X" banner, Crear sala, Modo práctica, Unirse por código, links to `/marcador` and `/preguntas` + "Cerrar sesión" button |
| `/sala/:codigo` | `PaginaSala` | The room. Renders by `sala.estado`: `esperando`→`VistaLobby`, `en_curso`→`VistaJuego`, `finalizada`→`VistaPodio` |
| `/marcador` | `PaginaMarcador` | All-time scoreboard table (highlights own username) |
| `/preguntas` | `PaginaPreguntas` | Card deck CRUD (create/edit/delete, paginated 20/page "Cargar más") |

`App.tsx` dispatches `restaurarSesion()` on mount and shows `PantallaCarga` until
`sesion.restaurada` is true — routes never render with an unknown session.

### Screen behavior details

- **PaginaInicio** — `FormularioRegistro` has two modes toggled by a text link
  ("¿Ya tienes usuario? Entra con tu nombre" ↔ "¿No tienes usuario? Créalo aquí"):
  **registro** dispatches `crearUsuario`, **login** dispatches `iniciarSesion` (same single
  name field, no password). Both validate locally (3–30 chars, no whitespace) first; server
  409/422/404 shown inline. When registro fails with **409** (name taken), a secondary
  button "Iniciar sesión como {username}" appears (driven by `sesion.errorEstado === 409`).
  The logged-in nav includes **"Cerrar sesión"**, dispatching the `cerrarSesion` thunk.
  The resume banner appears only if
  localStorage has `pqp_sala_codigo` AND `GET /api/salas/{codigo}` says the sala is not
  `finalizada` (on 404 the stored code is deleted). Join form normalizes input
  (`normalizarCodigoSala`: uppercase, strip non-alphanumerics) and disables submit until
  the code is 6 valid-alphabet chars. **"Modo práctica"** (`BotonPractica`, next to Crear
  sala) dispatches `crearPractica` and navigates to `/sala/{codigo}` on success — the
  backend creates the sala with 2 bots already joined (backend-api.md §4.5/§5.6), so the
  lobby fills to "3 conectados" by itself; REST errors (notably the 409 for an empty deck)
  surface as toasts.
- **PaginaSala** — redirects to `/` when there's no session; shows a status banner whenever
  `conexion !== 'conectado'` (Conectando… / Reconectando… / Sin conexión). Calls
  `useConexionSala(codigo)` (§7) which owns join+connect+cleanup.
- **VistaLobby** — big código + copy-to-clipboard button, live player list (`FichaJugador`:
  conectado dot, 👑 anfitrión, "(tú)"). Host sees "Iniciar partida", **disabled while
  connected players < 2 — that minimum is frontend-only, the backend does not enforce it**.
  Non-hosts see "Esperando a que {anfitrión} inicie…".
- **VistaJuego** — lazily loads predicciones (`cargarPredicciones`) once. Header: "Turno de
  {lector}", warning if lector disconnected, host-only "Finalizar partida" with inline
  confirm step. Body per round state (§8). `MarcadorLateral`: fixed bottom bar on mobile /
  right sidebar on md+, players sorted by points, lector highlighted.
- **VistaPodio** — reads `puntajes.marcadorFinal`; multiple 🏆 winners on ties; if
  `marcadorFinal` is null (e.g. arrived after reload) shows "Esta partida ya terminó" with
  the same exits. "Volver al inicio" dispatches `limpiarSala` + `limpiarMarcadorFinal` and
  removes `pqp_sala_codigo`.
- **PaginaPreguntas** — plain local state (no Redux). Cards are enunciado + 2 options
  (`FormularioPregunta` has three textareas: Pregunta, Opción 1, Opción 2). Create
  prepends; edit does a full-card update via `PUT /api/preguntas/{id}` and replaces the
  local row with the server response; delete removes. "Hay más" heuristic: last page was
  full (`pagina.length === 20`).

## 5. Redux store (5 slices)

`RootState` is derived from `rootReducer` (not the store) to avoid a circular type
reference with the WS middleware. Typed hooks in `store/hooks.ts`.

### `sesion` — who am I
State: `{ usuario, cargando, error, errorEstado, restaurada }` (`errorEstado` = HTTP status
of the last register/login failure — the 409 drives the "log in as X" shortcut).
Thunks: `crearUsuario(username)` → `POST /api/usuarios` and `iniciarSesion(username)` →
`POST /api/sesiones` — both receive `{token, usuario}` and persist token+id+username to
localStorage on success; `restaurarSesion()` → reads the stored **token**,
`GET /api/usuarios/actual`, clears storage if it fails, always ends with `restaurada=true`;
`cerrarSesion()` → dispatches `desconectarWs` + `limpiarSala` **first** (the middleware
still needs the state), then best-effort `DELETE /api/sesiones/actual`, then wipes all
`pqp_*` keys — UI flips to the register form because `usuario` becomes null.
Actions: `sesionExpirada` (dispatched by the global 401 handler wired in `store/index.ts`
via `establecerManejador401`, and on WS close 4001 — clears usuario+storage),
`limpiarErrorSesion`.

### `sala` — the room + current round (the heart of the app)
State:
```ts
{
  sala: Sala | null, cargando, error,
  conexion: 'desconectado'|'conectando'|'conectado'|'reconectando',
  motivoExpulsion: string | null,          // set on WS close 4003
  errorJuego: string | null,               // last WS `error` event detalle
  ronda: {
    id, etapa: 'leyendo'|'votando'|'resuelta'|null, pregunta,
    votosRecibidos, votosEsperados,
    miVoto: 1|2|null, miPrediccion: PrediccionClave|null,
    resultado: DatosResultadoRonda|null,
    desconocida: boolean,                  // true = round in progress but stage unknown (reconnect)
  }
}
```
REST thunks: `crearSala`, `crearPractica` (→ `POST /api/salas/practica`; same
pending/fulfilled/rejected handling as `crearSala`), `unirseSala(codigo)`, `sincronizarSala(codigo)` (the resync/
reconnection fetch — sets `ronda.desconocida=true` when sala is `en_curso` and no local
etapa), `iniciarPartida`, `finalizarPartida`.

**Outgoing WS intent actions** (reducers are no-ops or optimistic; `wsMiddleware`
intercepts and sends the frame): `conectarWs(codigo)`, `desconectarWs`, `robarCarta`,
`enviarPrediccion(clave)` (stores `miPrediccion`), `enviarVoto(1|2)` (stores `miVoto`),
`siguienteTurno`.

**Incoming WS actions** (dispatched by the middleware, one per server event):
`wsConectado(miUsuarioId)` (also marks *myself* `conectado=true` — the server never echoes
my own `jugador_unido`), `wsReconectando`, `wsDesconectado`, `wsExpulsado(razon)` (wipes
sala+ronda), `jugadorUnido` (marks connected or appends new player), `jugadorSalio`
(marks disconnected — never removes), `partidaIniciada` (estado→en_curso, assigns
orden_turno), `turnoActual` (sets counter, **resets the whole ronda substate**),
`cartaRobada` (etapa→leyendo), `prediccionRegistrada` (etapa→votando), `votoRegistrado`
(progress counters), `resultadoRonda` (etapa→resuelta, stores reveal, updates lector's
puntos), `partidaFinalizada` (estado→finalizada), `errorJuego(detalle)` (**clears
`miVoto`/`miPrediccion` so the user can retry — except when detalle is exactly
`'Ya votaste en esta ronda'`**), `limpiarErrorJuego`, `limpiarError`, `limpiarSala`.

Exports `calcularLector(sala)` — the modulo rule
(`orden_turno === turno_actual % jugadores.length`), same math as the backend.

### `puntajes` — scores outside the live sala
`marcadorFinal` (podium) is set from **two** sources: the WS `partidaFinalizada` action
(guests) and `finalizarPartida.fulfilled` (the host's REST response). `historico` +
`cargarMarcadorHistorico(usuarioId?)` → `GET /api/marcador`.

### `constantes` — prediction labels
`predicciones: [{clave, etiqueta}]`, `cargado`. Loaded once by VistaJuego via
`cargarPredicciones` → `GET /api/constantes/predicciones`. Never hardcode the labels.

### `ui` — toast queue
`notificar(mensaje, tipo: 'error'|'exito'|'info')` (prepare adds uuid) / `descartar(id)`.
`<Notificaciones/>` (global, aria-live) auto-dismisses each toast after 5 s.

## 6. WebSocket layer

**`ws/clienteWs.ts` — `ConexionSala`**: owns one raw WebSocket
(`urlWsSala(codigo, token)` → `ws(s)://…/ws/salas/{codigo}?token=…` — the session token,
read from `almacenamiento` by the middleware). Tracks
`cerradoIntencionalmente` so callbacks can tell a deliberate `cerrar()` from a drop.
Guards against non-JSON / envelope-less messages (warns and drops). `enviar()` silently
no-ops unless the socket is OPEN. Constructor takes `{onAbrir, onMensaje, onCierre}` —
injectable via factory for tests (unit tests never open real sockets).

**`ws/wsMiddleware.ts` — `crearWsMiddleware(fabricaConexion?)`**, registered at store
creation. Responsibilities:

1. **Send**: matches the six intent actions and writes the exact wire envelopes
   (`{evento, datos}` — see backend-api.md §5.3).
2. **Receive**: exhaustive switch mapping every server event to its `salaActions.*`
   dispatch; the `error` event becomes `errorJuego(detalle)`. Unknown events are warned
   and dropped (never-check keeps the union honest).
3. **Reconnect**: on unintentional close (≠4001/4003) dispatches `wsReconectando` and
   retries with backoff `[1s, 2s, 4s, 8s, 10s cap]`. **Every reopen is preceded by
   `sincronizarSala(codigo)`** (REST snapshot first, then socket) — this is the resync
   contract from backend-api.md §6.5.
4. **Expulsion**: close code **4003** → `wsExpulsado(reason)`, no retry (the hook below
   toasts it and navigates home). Close code **4001** (dead session token) additionally
   dispatches `sesionExpirada` first — the user lands back on the register/login form.
5. **Tab visibility**: a `visibilitychange` listener reconnects immediately (reset
   backoff, resync) when the tab becomes visible while disconnected — the mobile
   "lock/unlock phone" path.

## 7. `useConexionSala(codigo)` — room lifecycle hook (mounted by PaginaSala)

On mount (and whenever codigo/usuario changes):
1. `unirseSala(codigo)` (idempotent join).
2. If join succeeds → `sincronizarSala` → save `pqp_sala_codigo` → `conectarWs`.
3. **If join fails**: the backend answers 409 "La partida ya empezó" for `en_curso` salas
   *even for existing members* (it checks estado before membership — happens on tab reload
   mid-game). Workaround: `sincronizarSala` anyway, check membership in the snapshot; if
   member → proceed to connect; if not → toast + navigate `/`.
4. Cleanup on unmount: `desconectarWs`.

Also converts `motivoExpulsion` (→ toast, drop stored code, navigate `/`) and `errorJuego`
(→ toast + clear) into UI effects.

## 8. In-game UI state machine (VistaJuego body)

Driven by `ronda.etapa` + role selectors. Roles come from `seleccionadores/juego.ts`,
never from local assumptions:
`selectLector`, `selectSoyLector`, `selectSoyAnfitrion`, `selectMiJugador`,
`selectJugadoresOrdenadosPorPuntos`, `selectVotantesEsperados` (connected minus lector),
`selectJugadoresConectadosCount`.

| ronda state | Lector sees (`PanelLector`) | Others see (`PanelVotante`) |
|---|---|---|
| `etapa=null` (no round) | "Robar carta" button; if errorJuego is deck-exhausted, hint linking `/preguntas` | "El lector está leyendo la carta…" |
| `leyendo` (after `carta_robada`) | `SelectorPrediccion` — 4 buttons from constantes + confirm | same waiting text (card — enunciado above the two options — visible to all via `TarjetaDilema`; the enunciado `<p>` carries `data-testid="enunciado-carta"` for the E2E) |
| `votando` (after `prediccion_registrada`) | "Predicción guardada. Esperando los votos…" | Two big buttons **1 ☝️ / 2 ✌️** → `enviarVoto`; after `miVoto`: "Voto registrado ✓". `ProgresoVotos` bar (n/m) shows for everyone |
| `resuelta` (after `resultado_ronda`) | `PanelResultado` for everyone: result label, every vote colored by option, lector's prediction (etiqueta from constantes), ✅ +1 / ❌ falló, and a "Siguiente turno" button **only for lector or anfitrión** | idem |
| `desconocida=true` (reconnected mid-round) | `PanelRondaDesconocida`: "Hay una ronda en curso…" + speculative recovery actions — "Robar carta" (lector) / "Forzar siguiente turno" (anfitrión). If they don't apply, the backend rejects with an `error` toast, harmless | idem |

`turno_actual` (WS) resets `ronda` to empty → back to row 1 with the new lector.

## 9. API layer conventions

`clienteHttp` (`get/post/put/delete<T>`): base URL from `VITE_API_URL`; JSON bodies;
attaches `Authorization: Bearer <token>` automatically whenever `pqp_token` is stored;
`204 → undefined`; **every failure throws `ErrorApi { detalle, status }`** — network
failures get `status: 0` and detalle "Error de conexión con el servidor"; non-JSON error
bodies fall back to that same message. **Any 401 first invokes the handler registered via
`establecerManejador401`** (the store wires it to `sesionActions.sesionExpirada`). Thunks
catch with `detalleDeError(error)` (Spanish detalle for `ErrorApi`, **re-throws anything
else**) or `datosDeError(error)` (same but `{detalle, status}`, used by the sesion thunks).

Endpoint coverage (full contract in backend-api.md §4): `usuariosApi` (crear → `{token,
usuario}`, obtenerActual, obtener), `sesionesApi` (iniciar → login by username, cerrar →
logout), `salasApi` (crear, crearPractica, unirse, iniciar, finalizar — all five actor
calls are body-less, identity travels in the Bearer header —, obtener, obtenerPuntos,
actualizarPuntos, borrarPuntos — the puntos ones exist but no UI uses them yet), `preguntasApi` (listar
paginated, crear, obtener, actualizar — full-card PUT used by the edit flow —,
obtenerOpciones, actualizarOpciones — both options-only, no UI uses them —, eliminar —
always 204: the server hard-deletes never-played cards and soft-deletes played ones,
transparent to the client),
`marcadorApi` (obtenerHistorico), `constantesApi` (obtenerPredicciones).

## 10. Persistence (localStorage, all wrapped in try/catch — private mode safe)

| Key | Content | Written | Cleared |
|---|---|---|---|
| `pqp_usuario_id` | UUID of my Usuario | on `crearUsuario`/`iniciarSesion` success | `cerrarSesion`, `sesionExpirada`, failed restore |
| `pqp_username` | display name | idem | idem |
| `pqp_token` | bearer session token (UUID) — the actual identity | idem | idem |
| `pqp_sala_codigo` | last sala I connected to (powers the "Volver a la sala" banner) | in `useConexionSala` after join | expulsion, podium exit, 404 on banner check, **and any session wipe** (`limpiarSesion()` clears all four keys) |

## 11. Styling & a11y

Tailwind v4 tokens in `estilos/index.css` `@theme`: `primario` (violet scale), `acento`
(pink), **`opcion-1` cyan / `opcion-2` amber** (used consistently anywhere an option is
referenced: card, vote buttons, reveal), `exito`/`error`, dark surfaces
(`fondo`/`superficie`/`superficie-alta`), `font-display`. Dark-only (`color-scheme: dark`).
Mobile-first; `MarcadorLateral` is the main responsive pivot (bottom bar ↔ sidebar).
Animations: `animate-aparecer`, `animate-revelar` (keyframes in the same file, disabled
under `prefers-reduced-motion`). A11y habits used: `aria-live` on toasts/results/progress,
`role="status"`, `aria-label` on icon buttons, `useEnfoqueAlMontar` moves focus to page
containers on navigation/view change. Touch targets ≥ `min-h-11`.

## 12. Tests

- `tests/store/sesionSlice.test.ts` (mocked APIs — register/login store the token, 409
  keeps `errorEstado`, restore by token, `cerrarSesion` revokes + wipes storage + resets
  sala, `sesionExpirada`), `tests/store/salaSlice.test.ts`,
  `tests/seleccionadores/juego.test.ts`, `tests/ws/wsMiddleware.test.ts` (fake
  `ConexionSala` via the factory — asserts sent frames incl. the `?token=` connect arg,
  event dispatching, backoff, 4001 (session wipe, no retry), 4003, resync-before-reopen).
- `e2e/juego-completo.spec.ts`: 3 browser contexts, full game incl. mid-game reload
  resync, ties, podium, marcador. Needs backend on :8000 (use `scripts/e2e.sh` from repo
  root for the all-in-one run; Playwright starts Vite itself, `reuseExistingServer: true`).
  Gotcha: `robar_carta` draws a **random** pregunta from the whole DB (which persists
  across runs), so the spec never asserts the seeded card's text — it checks the card
  shows *some* enunciado via `getByTestId('enunciado-carta')`.
- `e2e/practica.spec.ts`: Modo práctica — 1 browser + the 2 server bots, up to 3 rounds
  until the human has been lector once (guaranteed by the modulo rotation), then podium
  with 3 rows. It branches on the **visible UI** (Robar carta vs. "El lector está
  leyendo…") instead of assuming roles; gotcha baked into it: Playwright's `isVisible()`
  does not retry, so it first `Promise.race`s the two panels' `waitFor` before checking
  which one won (the round header renders a React commit before the role panel).

## 13. Known limitations / gotchas (do not "rediscover" these)

1. **Mid-round reconnect is blind**: the REST snapshot has no ronda stage/pregunta →
   `ronda.desconocida` panel with speculative recovery buttons. Backend limitation.
2. **Stuck round**: if the last pending voter disconnects and no further vote arrives, the
   round hangs forever — resolution is only re-evaluated on vote arrival, and the host's
   force-turn only applies when the *lector* is disconnected. Backend fix required; the
   frontend cannot unstick it.
3. **Join-409 on reload mid-game** is expected and worked around in `useConexionSala` (§7).
4. **Min 2 players to start is a UI rule only** — the backend would happily start with 1.
5. The deck starts empty on a fresh DB; the game can't play a round until preguntas exist
   (create at `/preguntas`).
6. `salasApi` puntos endpoints (manual correction/reset) have no UI yet.

## 14. Pending work

None planned.

**Sesiones + Cerrar sesión** was implemented 2026-07-17: real bearer sessions
(`pqp_token`), login-by-username mode in `FormularioRegistro`, the "Cerrar sesión" nav
button, the global 401 → `sesionExpirada` handler, WS `?token=` + close 4001 handling,
and body-less actor calls in `salasApi`. E2E: `e2e/sesion.spec.ts`. Note `restaurarSesion`
still clears credentials on ANY restore failure (including transient network errors) —
pre-existing semantics, kept deliberately; it now discards a real token, so a flaky boot
logs you out (recoverable via login-by-name).

**Modo práctica** (single human + 2 server bots) was implemented 2026-07-15
(all 5 phases of [`../plans/pero-que-putas-practica.md`](../plans/pero-que-putas-practica.md)):
`BotonPractica` on inicio → `crearPractica` thunk → `POST /api/salas/practica`. From the
lobby on, the client treats bots exactly like human players — there is **no bot-specific
frontend code** beyond the button/thunk, by design (see backend-api.md §5.6). One behavior
to keep in mind when touching VistaJuego: when a bot is lector, `siguiente_turno` fires
from the server ~4–6.5 s after the reveal, so turn changes can arrive without any local
user action.
