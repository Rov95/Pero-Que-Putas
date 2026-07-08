# Plan: Modo Práctica — "Pero Qué Putas" (bots de práctica + botón en inicio)

> **Propósito:** plan completo y accionable para que un agente de Claude implemente el
> **modo práctica**: un solo jugador humano puede probar el juego completo de punta a punta
> (lobby → iniciar → rondas → finalizar → podio) contra **2 bots que juegan al azar**.
> Este documento NO contiene código de implementación: contiene estructura, nombres,
> comportamientos y criterios de aceptación verificables.
>
> **Repo:** `~/Desktop/Portfolio/Pero-Que-Putas` — backend FastAPI en `server/`, frontend
> Vite+React+TS+RTK en `client/`. Planes previos (contexto y estilo):
> `~/Desktop/plans/pero-que-putas-backend.md` y `~/Desktop/plans/pero-que-putas-frontend.md`.
>
> **Fecha:** 2026-07-07 · **Punto de partida verificado:** 61 tests de pytest en verde,
> 27 de vitest en verde, E2E de 3 navegadores en verde (`scripts/e2e.sh`).

---

## 0. Instrucciones para el agente ejecutor

1. Implementa las fases de la sección 5 **en orden estricto**. El usuario te pedirá ejecutar
   **UNA fase**; al terminar su puerta de verificación, **DETENTE** y espera confirmación
   explícita del usuario antes de tocar la siguiente. Cada fase repite esta instrucción.
2. Todos los textos visibles para el usuario (errores, labels, mensajes) van **en español**.
   Los nombres de dominio en el código también van en español (`practica`, `bots`,
   `crear_sala_practica`), consistente con el resto del repo.
3. Las decisiones de arquitectura ya están tomadas (sección 2): **no re-diseñar**. Las únicas
   cuestiones abiertas están en la sección 7 con recomendación por defecto: si el usuario no
   indica lo contrario, aplica la recomendación.
4. Regla de oro de este feature: **cero cambios en los servicios del game-loop existentes**
   (`app/services/juego.py`, `app/websocket/router.py`, `app/websocket/manager.py`,
   `app/websocket/eventos.py`). Los bots son clientes WS normales; si sientes la tentación de
   tocar el game-loop, detente y consulta la sección 6 (riesgos) o pregunta al usuario.
5. Los 61 tests de pytest y los 27 de vitest existentes deben seguir en verde en TODAS las
   puertas de verificación. Una fase no está terminada si rompe algo previo.
6. Ejecuta los tests del backend desde `server/` con `uv run pytest` (harness pgserver
   embebido, `asyncio_mode=auto`, sin Docker). Frontend desde `client/` con npm.

---

## 1. Resumen de contexto (qué existe hoy — confirmación de entendimiento)

- **Juego:** salas con código de 6 caracteres; el anfitrión inicia/finaliza por REST; cada
  turno un **lector** roba carta (`robar_carta`), hace **predicción secreta**
  (`prediccion_secreta`, una de `mayoria_1|todos_1|mayoria_2|todos_2`), los demás votan
  `1|2` (`voto`); la ronda se resuelve sola al llegar el último voto esperado y se difunde
  `resultado_ronda`; `siguiente_turno` (lector o anfitrión) rota el lector.
- **WS:** `ws://…/ws/salas/{codigo}?usuario_id={uuid}`, sobre `{"evento","datos"}` en ambas
  direcciones. Al conectar, el servidor pone `conectado=true` en `sala_jugadores` y difunde
  `jugador_unido`; al desconectar, `conectado=false` + `jugador_salio`. Errores de reglas →
  evento `error {detalle}` solo al socket infractor, nunca cierran el socket.
- **Hecho clave 1:** `votos_esperados` (`app/services/juego.py:111-115`) cuenta solo
  jugadores **conectados** que no son el lector → un bot que no esté `conectado=true` jamás
  votaría ni contaría. Por eso los bots DEBEN ser clientes WS reales.
- **Hecho clave 2:** el backend no impone mínimo de jugadores para iniciar, pero el lobby del
  cliente (`client/src/paginas/sala/VistaLobby.tsx:71`) deshabilita "Iniciar partida" con
  `conectados < 2` → con 2 bots conectados el humano puede iniciar solo.
- **Hecho clave 3:** ya existe un patrón probado de cliente WS **in-process** contra la
  propia app ASGI: `httpx_ws.aconnect_ws` + `ASGIWebSocketTransport(app=…)`
  (`server/tests/test_juego_websocket.py:32-46` y `test_e2e.py`). Los bots reutilizan
  exactamente ese patrón, pero desde código de aplicación.
- **Hecho clave 4:** `robar_carta` responde 409 "No quedan preguntas disponibles" cuando la
  sala agotó el mazo; la BD arranca con cero preguntas.
- **Usernames:** únicos globales case-insensitive, patrón `^\S+$`, 3–30 caracteres
  (validación en schema + `app/services/usuarios.py`).
- **Harness de tests:** `server/tests/conftest.py` levanta Postgres embebido (pgserver) y
  crea la app con `dependency_overrides` de sesión. E2E real: `scripts/e2e.sh`
  (pgserver → alembic → uvicorn :8000 → Playwright `client/e2e/juego-completo.spec.ts` con
  3 navegadores, **sin Docker**). Dev local: `scripts/dev.sh`.

**Qué agrega este plan:** (a) endpoint `POST /api/salas/practica` que crea una sala con el
humano como anfitrión + 2 usuarios bot ya unidos, y lanza sus tareas de cliente WS;
(b) runtime `BotJugador` con estrategia 100 % aleatoria y retrasos con jitter para que el
humano pueda mirar; (c) botón "Modo práctica" en la página de inicio del cliente.

---

## 2. Decisiones de arquitectura (tomadas — no re-litigar)

| # | Tema | Decisión | Razón |
|---|---|---|---|
| 1 | Naturaleza de los bots | **Server-side, conectados como clientes WS reales a su propia app in-process** vía `httpx_ws.aconnect_ws` + `ASGIWebSocketTransport(app=…)` (el endpoint usa `request.app` para que los overrides de tests apliquen) | Los bots obtienen `conectado=true` (requisito de los hechos clave 1 y 2), todos los broadcasts llegan al humano sin cambios y el game-loop existente no se toca |
| 2 | Dependencias | Promover `httpx` y `httpx-ws` del grupo `dev` a **dependencias principales** en `server/pyproject.toml` | El runtime de bots los importa en producción |
| 3 | Módulo nuevo | `server/app/bots/` con tres piezas: `fabrica.py` (crear usuarios bot), `jugador.py` (runtime `BotJugador`), `registro.py` (registro de tareas por sala + ciclo de vida) | Aislado del resto; borrable sin tocar el juego |
| 4 | Endpoint nuevo | `POST /api/salas/practica`, body `{usuario_id}` → 201 `SalaLeer`. Internamente: valida preguntas (§7-C1) → reutiliza `crear_sala` (`services/salas.py:42`) → crea 2 usuarios bot → los une con `unirse_a_sala` (`services/salas.py:63`) → lanza sus tareas WS → devuelve la sala | El humano queda anfitrión y usa el flujo normal de lobby/iniciar/finalizar; cero endpoints de juego nuevos |
| 5 | Estrategia de los bots | **Cero estrategia:** predicción aleatoria uniforme entre los 4 valores del enum; voto aleatorio uniforme `1|2` | Es una herramienta de prueba, no un rival |
| 6 | Retrasos | Configurables en `Settings` (`app/config.py`), con **jitter** aleatorio; los tests los ponen ≈0 | Humano puede observar; el jitter reduce carreras de votos simultáneos |
| 7 | Nombres de bot | `Bot-{Apodo}-{SUFIJO}` (ej. `Bot-Luna-7GQ2`): apodo de una lista corta en español + sufijo aleatorio de 4 caracteres del alfabeto de códigos de sala; cumple `^\S+$` y 3–30; reintento con sufijo nuevo ante colisión | Unicidad global case-insensitive de usernames |
| 8 | Seguridad/limpieza | Vida máxima por tarea de bot (configurable) + registro con cancelación por sala y al apagar la app | Salas de práctica abandonadas no filtran tareas |
| 9 | Marcador histórico | `finalizar` escribirá filas de bots en `marcador_historico` (`services/salas.py:122-160`): **se acepta tal cual** (§7-C2) | Es lo más simple; es una herramienta de desarrollo |
| 10 | Frontend | Cambio mínimo: `crearPractica` en `salasApi.ts`, thunk `crearPractica` clon de `crearSala` (`salaSlice.ts:71-82`), componente `BotonPractica.tsx` con `variante="secundario"` junto a `<BotonCrearSala />` en `PaginaInicio.tsx:63`, navegar a `/sala/{codigo}` al éxito. **Nada más**: los bots aparecen como jugadores conectados normales | El lobby, juego y podio ya funcionan sin saber qué es un bot |

### 2.1 Protocolo de comportamiento del bot (contrato de `BotJugador`)

Estado interno mínimo: `soy_lector: bool` (derivado del último `partida_iniciada` /
`turno_actual` recibido, comparando `datos.lector.usuario_id` con el propio).

| Evento recibido | Reacción si SOY lector | Reacción si NO soy lector |
|---|---|---|
| `partida_iniciada` / `turno_actual` | actualizar lector → retraso con jitter → enviar `robar_carta {}` | actualizar lector; nada más |
| `carta_robada` | retraso → enviar `prediccion_secreta {prediccion: aleatoria entre las 4}` | nada (esperar) |
| `prediccion_registrada` | nada (esperar votos) | retraso con jitter → enviar `voto {opcion: 1\|2 aleatoria}` |
| `voto_registrado` | ignorar | ignorar |
| `resultado_ronda` | retraso **largo** (§7-C3, para que el humano lea el resultado) → enviar `siguiente_turno {}` | nada |
| `partida_finalizada` | terminar la tarea limpiamente | terminar la tarea limpiamente |
| `jugador_unido` / `jugador_salio` | ignorar | ignorar |
| `error` | loguear warning y seguir (nunca crashear) | ídem |
| evento desconocido | loguear warning y seguir | ídem |
| cierre del socket / cancelación / vida máxima agotada | terminar la tarea (el propio endpoint WS del servidor ya difunde `jugador_salio` y pone `conectado=false`) | ídem |

Notas de robustez del runtime (comportamiento, no código):
- El bot **nunca** dirige el ritmo del humano: si el humano es lector, el bot solo espera y vota.
- Todo `send` va precedido de su retraso; los retrasos leen `settings` **en el momento de
  usarse** (no capturados al importar) para que los tests puedan parchearlos.
- La tarea completa corre bajo un tope de vida máxima; al expirar, cierra el socket y termina.
- Excepciones inesperadas dentro del loop: loguear y terminar la tarea (jamás propagar al
  servidor ni reintentar en bucle).

---

## 3. Diseño backend (estructura y nombres)

```
server/app/bots/
├── __init__.py
├── fabrica.py      # crear_usuarios_bot(sesion, cantidad) -> list[Usuario]
│                   #   nombres §2-7; reintenta ante colisión (máx. N intentos, luego 500)
├── jugador.py      # clase BotJugador(app, codigo, usuario_id, username)
│                   #   método asíncrono correr(): conecta el WS y ejecuta la tabla §2.1
└── registro.py     # RegistroBots (instancia única a nivel de módulo):
                    #   iniciar_bots(app, codigo, bots) -> crea asyncio.Tasks con tope de vida
                    #   detener_bots(codigo)            -> cancela y espera las tareas de esa sala
                    #   detener_todos()                 -> para el shutdown de la app y los tests
                    #   auto-poda: cada tarea se remueve del registro al terminar (done callback)
```

Piezas que se **modifican** (mínimamente):

- `server/pyproject.toml` — mover `httpx` y `httpx-ws` a `[project].dependencies`.
- `server/app/config.py` — nuevos campos de `Settings` (nombres exactos):
  `bots_retraso_min_ms`, `bots_retraso_max_ms`, `bots_retraso_siguiente_turno_ms`,
  `bots_vida_maxima_segundos` (defaults en §7-C3).
- `server/app/services/salas.py` — nueva función `crear_sala_practica(sesion, usuario_id)`:
  valida que exista al menos 1 pregunta (si no, `ErrorAplicacion` 409 con el mensaje de
  §7-C1) → `crear_sala` → `crear_usuarios_bot(…, 2)` → `unirse_a_sala` por cada bot →
  devuelve la sala recargada + la lista de bots (id y username). No lanza tareas (eso es
  responsabilidad del router, que tiene `request.app`).
- `server/app/schemas/sala.py` — `PracticaCrear {usuario_id}` (mismo patrón que
  `SalaCrear`/`IniciarSala`).
- `server/app/routers/salas.py` — handler `POST /api/salas/practica` (201, `SalaLeer`):
  llama al servicio y luego a `registro.iniciar_bots(request.app, codigo, bots)`.
- `server/app/main.py` — en el apagado de la app, llamar `detener_todos()` del registro
  (lifespan o evento de shutdown; único cambio en `main.py`).

**Errores del endpoint:** 404 "Usuario no encontrado" (lo da el servicio existente),
409 sin preguntas (§7-C1). Cuerpo de error estándar `{"detalle": …}`.

---

## 4. Diseño frontend (estructura y nombres)

- `client/src/api/salasApi.ts` — nuevo método `crearPractica(body: AccionSalaBody)` →
  `POST /api/salas/practica`, devuelve `Sala`. Sin tipos nuevos: reutiliza `AccionSalaBody`
  y `Sala` existentes.
- `client/src/store/slices/salaSlice.ts` — thunk `crearPractica` clon de `crearSala`
  (líneas 71-82: exige sesión, `rejectWithValue(detalleDeError(...))`) + sus tres casos en
  `extraReducers` idénticos a los de `crearSala` (pending → `cargando`, fulfilled → asigna
  `state.sala`, rejected → `error`).
- `client/src/paginas/inicio/BotonPractica.tsx` — clon de `BotonCrearSala.tsx`: despacha
  `crearPractica()`; al éxito navega a `/sala/{codigo}`; al fallo, toast con
  `resultado.payload` (así el 409 de "sin preguntas" del backend llega al usuario tal cual)
  o fallback "No se pudo crear la sala de práctica". Usa `<Boton variante="secundario">`,
  texto: **"Modo práctica"**.
- `client/src/paginas/inicio/PaginaInicio.tsx` — renderizar `<BotonPractica />`
  inmediatamente después de `<BotonCrearSala />` (línea 63).

**Nada más en el cliente.** El lobby muestra 3 jugadores (los bots llegan como
`jugador_unido` normales), el gate de "Iniciar partida" se satisface, y el juego/podio no
distinguen bots de humanos.

---

## 5. Plan de implementación — exactamente 5 fases

### Fase 1 — Backend REST: fábrica de bots + servicio + endpoint (sin runtime todavía)

**Objetivo:** `POST /api/salas/practica` crea la sala con humano anfitrión + 2 usuarios bot
unidos y validación de preguntas. Los bots aún NO se conectan (eso es la Fase 2).

**Archivos:** crear `app/bots/__init__.py`, `app/bots/fabrica.py`,
`tests/test_salas_practica.py`; modificar `server/pyproject.toml`,
`app/services/salas.py`, `app/schemas/sala.py`, `app/routers/salas.py`.

- [ ] Promover `httpx` y `httpx-ws` a dependencias principales (`uv lock` actualizado).
- [ ] `fabrica.crear_usuarios_bot`: nombres según §2-7, unicidad garantizada con reintentos.
- [ ] `crear_sala_practica` en `services/salas.py` según §3 (incluida la validación 409 de
      preguntas con el mensaje de §7-C1).
- [ ] Schema `PracticaCrear` + handler `POST /api/salas/practica` → 201 `SalaLeer`.
- [ ] Tests en `tests/test_salas_practica.py`: (a) 201 con 3 `jugadores`, anfitrión = humano,
      2 usernames que empiezan por `Bot-` y cumplen `^\S+$`; (b) los 2 usuarios bot existen
      en `GET /api/usuarios/{id}`; (c) sin preguntas en la BD → 409 con el detalle de §7-C1;
      (d) `usuario_id` inexistente → 404; (e) dos prácticas seguidas no chocan por nombres.

**Puerta de verificación:**
`cd server && uv run pytest tests/test_salas_practica.py -q` → todos en verde;
`uv run pytest -q` → **61 existentes + nuevos, todos en verde**;
`uv run python -c "import httpx, httpx_ws"` funciona con el entorno de producción (sin grupo dev).

**DETENTE aquí.** No continúes con la siguiente fase hasta que el usuario lo confirme.

---

### Fase 2 — Runtime de bots: `BotJugador` + registro + conexión desde el endpoint

**Objetivo:** al crear una sala de práctica, los 2 bots se conectan por WS in-process,
quedan `conectado=true` y juegan una ronda completa según la tabla §2.1.

**Archivos:** crear `app/bots/jugador.py`, `app/bots/registro.py`,
`tests/test_bots_runtime.py`; modificar `app/config.py` (retrasos y vida máxima),
`app/routers/salas.py` (lanzar bots con `request.app`), `app/main.py` (shutdown →
`detener_todos()`).

- [ ] `BotJugador.correr()` implementa exactamente la tabla §2.1 (incluye: retrasos con
      jitter leídos de `settings` en runtime; `error` y eventos desconocidos se loguean y se
      ignoran; terminación limpia con `partida_finalizada`, cierre de socket o cancelación).
- [ ] `RegistroBots` con `iniciar_bots` / `detener_bots` / `detener_todos`, tope de vida
      máxima por tarea y auto-poda al terminar.
- [ ] Endpoint de práctica lanza las tareas tras crear la sala; shutdown de la app cancela todo.
- [ ] Tests en `tests/test_bots_runtime.py` (con retrasos parcheados a ≈0 sobre
      `app.config.settings`): (a) tras `POST /api/salas/practica`, sondear
      `GET /api/salas/{codigo}` hasta ver a los 2 bots con `conectado=true` (timeout
      acotado); (b) conectar un socket de prueba como humano, `iniciar` por REST y jugar
      **una ronda completa** cubriendo ambas ramas según quién salga lector (humano lector:
      el humano roba y predice, los bots votan solos → llegan 2 `voto_registrado` +
      `resultado_ronda`; bot lector: llegan `carta_robada` y `prediccion_registrada` sin
      intervención, el humano vota, el otro bot vota → `resultado_ronda`, y el bot lector
      dispara `siguiente_turno` → llega `turno_actual`); (c) `detener_bots(codigo)` deja el
      registro vacío y los bots aparecen `conectado=false`.

**Puerta de verificación:**
`cd server && uv run pytest tests/test_bots_runtime.py -q` → verde;
`uv run pytest -q` → **toda la suite en verde** (61 existentes + Fase 1 + Fase 2), sin
warnings de tareas asyncio pendientes ni sockets sin cerrar al finalizar pytest.

**DETENTE aquí.** No continúes con la siguiente fase hasta que el usuario lo confirme.

---

### Fase 3 — Partida de práctica completa + robustez del ciclo de vida

**Objetivo:** demostrar el flujo entero en integración (1 socket humano de prueba + 2 bots,
≥3 rondas, finalizar, marcador) y cerrar los edge cases de limpieza.

**Archivos:** crear `tests/test_practica_e2e.py`; ajustes menores en `app/bots/*` solo si
los tests destapan defectos (documentarlos en el commit).

- [ ] Test de partida completa (retrasos ≈0): crear práctica → humano conecta → iniciar →
      jugar **al menos 3 rondas** (con 3 jugadores y rotación, el humano y ambos bots pasan
      por el rol de lector al menos una vez; el helper del test decide su acción según el
      lector anunciado en `turno_actual`) → `finalizar` por REST → `partida_finalizada`
      recibido por el humano → `GET /api/marcador` contiene filas de los 3 (bots incluidos,
      §2-9) → el registro de bots queda vacío solo, sin `detener_bots` manual.
- [ ] Test de sala abandonada: crear práctica con `bots_vida_maxima_segundos` parcheado a un
      valor mínimo; sin que nadie inicie, las tareas terminan solas dentro del tope y los
      bots quedan `conectado=false`.
- [ ] Test de carrera de votos: ronda donde los 2 bots votan (humano lector) repetida varias
      veces en el mismo test → siempre exactamente **un** `resultado_ronda` y
      `puntos_lector` coherente (vigila el riesgo R1 de §6).
- [ ] Revisión de fugas: ningún test deja tareas vivas (comprobar el registro al final).

**Puerta de verificación:**
`cd server && uv run pytest -q` → **toda la suite en verde** (los 61 originales intactos +
todo lo nuevo), tiempo total razonable (<2 min) y sin tareas colgadas al salir.

**DETENTE aquí.** No continúes con la siguiente fase hasta que el usuario lo confirme.

---

### Fase 4 — Frontend: API + thunk + botón "Modo práctica"

**Objetivo:** el humano puede crear la sala de práctica desde la página de inicio y llegar
al lobby con los 3 jugadores; el resto de la UI no cambia.

**Archivos:** crear `client/src/paginas/inicio/BotonPractica.tsx`; modificar
`client/src/api/salasApi.ts`, `client/src/store/slices/salaSlice.ts`,
`client/src/paginas/inicio/PaginaInicio.tsx`, `client/src/tests/store/salaSlice.test.ts`.

- [ ] `salasApi.crearPractica` según §4 (sin tipos nuevos).
- [ ] Thunk `crearPractica` + 3 casos de `extraReducers` espejo de `crearSala`.
- [ ] `BotonPractica.tsx` (variante `secundario`, texto "Modo práctica", navegación y toast
      de error según §4) colocado justo debajo de `<BotonCrearSala />` en `PaginaInicio.tsx`.
- [ ] Vitest en `salaSlice.test.ts`: `crearPractica.fulfilled` asigna `state.sala`;
      `crearPractica.rejected` deja `sala=null` y guarda `error`; `pending` activa `cargando`.

**Puerta de verificación:**
`cd client && npm run lint && npx tsc -b && npm test && npm run build` — todo en verde
(27 tests existentes + los nuevos), build sin warnings nuevos.

**DETENTE aquí.** No continúes con la siguiente fase hasta que el usuario lo confirme.

---

### Fase 5 — Verificación E2E con navegador real + documentación

**Objetivo:** una persona (Playwright con 1 solo navegador) juega una partida de práctica
completa contra los bots sobre el stack real (pgserver → alembic → uvicorn → Vite), se
corrigen los hallazgos y se documenta el feature. **Sin Docker.**

**Archivos:** crear `client/e2e/practica.spec.ts`; modificar `README.md` (raíz),
`client/README.md`, `server/README.md`; `scripts/e2e.sh` solo si hace falta exportar
retrasos de bots reducidos (variables de entorno de `Settings`).

- [ ] Spec Playwright (mismo estilo que `client/e2e/juego-completo.spec.ts`): sembrar ≥3
      preguntas por API → registrar un usuario en **un único contexto de navegador** → clic
      en "Modo práctica" → URL `/sala/…` → el lobby muestra 3 jugadores y llega a
      "3 conectados" → "Iniciar partida" habilitado → jugar rondas hasta que el humano haya
      sido lector al menos una vez, ramificando por la UI visible (si aparece "Robar carta"
      soy lector: robar + predecir y ver a los bots votar; si no, votar cuando se abra la
      votación y ver el resultado; los `siguiente_turno` de rondas con bot lector llegan
      solos) → finalizar → podio visible con 3 filas.
- [ ] Ajustar tiempos: si los retrasos por defecto (§7-C3) acercan el spec al timeout,
      exportar en `scripts/e2e.sh` retrasos menores para los bots vía entorno
      (documentarlo); NO bajar los defaults de producción por esto.
- [ ] Smoke manual con `./scripts/dev.sh`: jugar una práctica completa en el navegador de
      verdad, verificando que los retrasos por defecto se sienten "humanos" y que el
      resultado de ronda es legible antes del `siguiente_turno` del bot lector.
- [ ] Corregir cualquier hallazgo (backend o frontend) repitiendo las puertas previas.
- [ ] READMEs: sección "Modo práctica" (qué es, botón, endpoint `POST /api/salas/practica`,
      variables `bots_*` de configuración, nota de que los bots escriben en el marcador
      histórico).

**Puerta de verificación:**
`./scripts/e2e.sh` → los DOS specs de Playwright en verde (el de 3 jugadores existente y el
nuevo de práctica); `cd server && uv run pytest -q` en verde; `cd client && npm test` en
verde. Con esto el feature queda cerrado.

**DETENTE aquí.** Fase final: no hagas nada más hasta que el usuario lo confirme.

---

## 6. Riesgos técnicos (con mitigación decidida)

- **R1 — Carrera de votos simultáneos de los 2 bots** (humano lector): dos `voto` casi a la
  vez podrían, en teoría, disparar dos resoluciones (la comprobación
  `votos_recibidos >= votos_esperados` no es atómica entre sesiones). Mitigación: jitter en
  los retrasos (§2-6) + test dedicado en Fase 3. Si el test lo reproduce, **consultar al
  usuario** antes de tocar `juego.py` (violaría la regla de oro §0-4); la corrección mínima
  aceptable sería una guarda de idempotencia en la resolución.
- **R2 — El bot lector avanza el turno y el humano no llega a leer el resultado.**
  Mitigación: retraso específico y más largo para `siguiente_turno` (§7-C3), validado en el
  smoke manual de Fase 5.
- **R3 — `uvicorn --reload` en dev mata las tareas de bots al recargar.** Aceptado: es una
  herramienta de desarrollo; crear otra sala de práctica lo resuelve. Documentar en README.
- **R4 — Cada bot mantiene su sesión de BD viva mientras dura el socket** (igual que
  cualquier jugador WS): +2 conexiones por sala de práctica. Aceptado; la vida máxima (§2-8)
  acota el peor caso.
- **R5 — Tests colgados si un bot no termina.** Mitigación: timeouts acotados en todos los
  helpers de test (patrón `_drenar_jugador_unido` existente) + `detener_todos()` disponible
  para teardown.

## 7. Cuestiones abiertas (aplicar la recomendación si el usuario no dice lo contrario)

- **C1 — Mínimo de preguntas para crear una práctica.** `robar_carta` da 409 al agotarse el
  mazo, y con 0 preguntas la partida es imposible. *Recomendación:* exigir **≥1 pregunta**
  al crear la práctica y responder 409 con detalle:
  «No hay preguntas disponibles. Crea algunas en la pantalla de preguntas antes de practicar.»
  (Alternativa: exigir ≥3 para garantizar 3 rondas; no necesario para el MVP.)
- **C2 — Filas de bots en `marcador_historico`.** *Recomendación:* **aceptarlo** (decisión
  §2-9): es lo más simple y es una herramienta de prueba. Alternativa NO recomendada: campo
  `es_practica` en salas + migración Alembic + filtro en `GET /api/marcador` (coste alto,
  beneficio bajo hoy; revisitar si el marcador histórico se vuelve "serio").
- **C3 — Valores por defecto de los retrasos.** *Recomendación:*
  `bots_retraso_min_ms=800`, `bots_retraso_max_ms=2500` (uniforme con jitter para robar /
  predecir / votar), `bots_retraso_siguiente_turno_ms=4000` (base + jitter hasta
  `bots_retraso_max_ms` extra, para que el humano lea el resultado),
  `bots_vida_maxima_segundos=1800` (30 min). Tests: todo ≈0 salvo la vida máxima del test
  dedicado.
- **C4 — Número de bots.** *Recomendación:* **fijo en 2** (mínimo que habilita mayoría/empate
  y el gate del lobby). Hacerlo configurable en el body sería trivial más adelante.
- **C5 — Usuarios bot nuevos en cada práctica vs. reutilizados.** *Recomendación:* **crear
  usuarios nuevos** en cada práctica (sufijo aleatorio): evita todo conflicto de unicidad y
  de sesiones concurrentes. Coste aceptado: crecen las tablas `usuarios` y
  `marcador_historico` con bots (coherente con C2).
