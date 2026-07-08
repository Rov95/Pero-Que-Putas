# Plan de Arquitectura Frontend — Pero Qué Putas

> **Propósito:** plan completo y accionable para que un agente de Claude implemente el frontend
> del juego de fiesta "Pero Qué Putas" (React + TypeScript + Vite + Tailwind CSS + Redux Toolkit,
> tiempo real con WebSockets). Este documento NO contiene código de implementación: contiene
> estructura, tipos descritos conceptualmente y pasos ordenados por fases.
>
> **Fuente de verdad del backend:** `~/Desktop/Context/PQP/backend-api.md` (extraído del código
> real en `~/Desktop/Portfolio/Pero-Que-Putas/server`, 2026-07-07). No inventar endpoints ni
> eventos que no aparezcan en la sección 1 de este plan.
>
> **Ubicación del proyecto frontend:** `~/Desktop/Portfolio/Pero-Que-Putas/client` (carpeta ya
> existe, vacía).

---

## 0. Instrucciones para el agente ejecutor

1. Implementa las fases de la sección 8 **en orden**; cada fase tiene criterios de aceptación
   verificables. No avances de fase sin cumplirlos.
2. Todos los textos visibles para el usuario van **en español** (botones, errores, labels,
   estados vacíos). Los nombres de dominio en el código también van en español para ser
   consistentes con el backend (`sala`, `ronda`, `lector`, `prediccion`, …).
3. Las decisiones de arquitectura ya están tomadas (sección 2). Las únicas cuestiones abiertas
   están en la sección 9 con una recomendación por defecto: si el usuario no indica lo
   contrario, aplica la recomendación.
4. El backend corre en `http://localhost:8000` con CORS para `http://localhost:5173` (puerto
   por defecto de Vite). No cambiar el puerto del dev server.

---

## 1. Resumen extraído del backend (confirmación de entendimiento)

### 1.1 Juego y configuración base

- Party game en español tipo "¿Qué prefieres?": jugadores en una **sala** (código de 6
  caracteres, alfabeto `23456789ABCDEFGHJKMNPQRSTUVWXYZ`, siempre mayúsculas).
- El **anfitrión** (creador de la sala) inicia y finaliza la partida. Cada ronda un jugador es
  el **lector**: roba una carta (pregunta con Opción 1 / Opción 2), hace una **predicción
  secreta** del voto grupal, y los demás votan `1` o `2`. Predicción estricta (`mayoria_1` NO
  acierta si el resultado es `todos_1`). Acierto = 1 punto para el lector. `empate` = nadie
  puntúa. El lector no vota.
- Base URL: `http://localhost:8000` — REST bajo `/api`, WebSocket bajo `/ws`.
- IDs = UUID (string). Timestamps ISO-8601.
- **Sin autenticación**: el cliente se identifica enviando `usuario_id` en los bodies REST y en
  el query string del WS. Hay que persistir `usuario_id` en localStorage (perderlo = perder la
  identidad; los usernames son únicos globales case-insensitive → re-crear da 409).
- **Todo error, de cualquier status, tiene el body** `{ "detalle": "<mensaje en español>" }`
  (incluye 422 de validación).

### 1.2 Endpoints REST

| Método y ruta | Body / Query | Respuesta OK | Errores relevantes |
|---|---|---|---|
| `GET /api/salud` | — | `{estado:"ok"}` | — |
| `POST /api/usuarios` | `{username}` (3–30 chars, sin espacios `^\S+$`) | `201 Usuario` | `409` nombre en uso · `422` |
| `GET /api/usuarios/{id}` | — | `Usuario` | `404` |
| `GET /api/preguntas` | `?desplazamiento=0&limite=20` (límite 1–100) | `Pregunta[]` | — |
| `POST /api/preguntas` | `{opcion_1, opcion_2}` | `201 Pregunta` | `422` |
| `GET /api/preguntas/{id}` | — | `Pregunta` | `404` |
| `GET /api/preguntas/{id}/opciones` | — | `{opcion_1, opcion_2}` | `404` |
| `PUT /api/preguntas/{id}/opciones` | `{opcion_1, opcion_2}` | `{opcion_1, opcion_2}` | `404` |
| `DELETE /api/preguntas/{id}` | — | `204` | `404` |
| `GET /api/constantes/predicciones` | — | `[{clave, etiqueta}]` (las 4 predicciones) | — |
| `POST /api/salas` | `{usuario_id}` | `201 Sala` (creador = anfitrión, auto-unido) | `404` usuario |
| `POST /api/salas/{codigo}/unirse` | `{usuario_id}` | `200 Sala` (**idempotente**) | `404` sala/usuario · `409` "La partida ya empezó" |
| `GET /api/salas/{codigo}` | — | `Sala` (**endpoint de reconexión**) | `404` |
| `POST /api/salas/{codigo}/iniciar` | `{usuario_id}` (anfitrión) | `200 Sala` + broadcast WS | `403` no anfitrión · `409` ya empezó |
| `POST /api/salas/{codigo}/finalizar` | `{usuario_id}` (anfitrión) | `200 {sala, marcador_final}` + broadcast WS | `403` · `409` no en curso |
| `GET /api/salas/{codigo}/puntos` | — | `PuntoJugador[]` | `404` |
| `PUT /api/salas/{codigo}/puntos/{usuario_id}` | `{puntos}` | `PuntoJugador` | `404` |
| `DELETE /api/salas/{codigo}/puntos` | — | `204` | `404` |
| `GET /api/marcador` | `?usuario_id=` opcional | `MarcadorHistoricoEntrada[]` (desc por puntos) | — |

### 1.3 Protocolo WebSocket

- Conexión: `ws://localhost:8000/ws/salas/{codigo}?usuario_id={uuid}`, **después** de unirse por
  REST. Fallo de validación → el servidor cierra con **código 4003** y razón en español
  ("Sala no encontrada" / "No perteneces a esta sala") → volver a la pantalla de unirse
  mostrando la razón.
- Sobre (ambas direcciones): `{ "evento": "<nombre>", "datos": {...} }`.
- Al conectar: el servidor pone `conectado=true` y emite `jugador_unido` a **los demás** (nunca
  recibes tu propio join). Al desconectar: `conectado=false` + `jugador_salio` a los demás.
- La resolución de ronda solo espera a votantes **conectados** (un desconectado no bloquea).

**Cliente → Servidor:**

| evento | datos | quién | errores (evento `error` solo al emisor) |
|---|---|---|---|
| `robar_carta` | `{}` | lector actual | 403 no lector · 409 no en curso · 409 ronda activa · 409 "No quedan preguntas disponibles" |
| `prediccion_secreta` | `{prediccion}` | lector actual | 403 · 409 sin ronda esperando predicción · 400 "Predicción inválida" |
| `voto` | `{opcion: 1\|2}` | todos MENOS el lector | 403 "El lector no vota" · 409 etapa incorrecta · 409 "Ya votaste en esta ronda" · 400 "Voto inválido" |
| `siguiente_turno` | `{}` | lector O anfitrión | 403 · 409 "Termina la ronda actual antes de continuar" (excepción: si el lector está desconectado, el anfitrión SÍ puede forzarlo) |
| otro | — | — | 400 "Evento desconocido: <nombre>" |

Los errores de reglas de negocio **nunca cierran el socket**: llegan como
`{evento:"error", datos:{detalle}}` solo al socket infractor.

**Servidor → Cliente (broadcast a toda la sala salvo indicación):**

| evento | datos | cuándo |
|---|---|---|
| `jugador_unido` | `{usuario_id, username}` | alguien conecta (no se envía a ese alguien) |
| `jugador_salio` | `{usuario_id, username}` | alguien desconecta |
| `partida_iniciada` | `{orden:[{usuario_id, username, orden_turno}], lector:{usuario_id, username}}` | anfitrión llamó REST `iniciar`; `orden` viene ordenado |
| `turno_actual` | `{numero, lector:{usuario_id, username}}` | tras `partida_iniciada` y tras cada `siguiente_turno` aceptado |
| `carta_robada` | `{ronda_id, pregunta:{id, opcion_1, opcion_2}}` | el lector robó carta (todos ven las opciones) |
| `prediccion_registrada` | `{lector_id}` — **nunca incluye la predicción** | el lector fijó predicción → se abre la votación |
| `voto_registrado` | `{votos_recibidos, votos_esperados}` — **nunca dice quién votó qué** | cada voto aceptado (mostrar progreso n/m) |
| `resultado_ronda` | `{votos:[{usuario_id, username, opcion}], resultado, prediccion, acierto, puntos_lector}` | automático al llegar el último voto esperado: la gran revelación |
| `partida_finalizada` | `{marcador_final: MarcadorFinalEntrada[]}` | anfitrión llamó REST `finalizar` |
| `error` | `{detalle}` | solo al socket que envió un evento inválido |

**Máquina de estados de la ronda** (dirige la pantalla de juego):

```
(sin ronda) --robar_carta--> "leyendo" (todos: carta_robada; lector: selector de predicción)
            --prediccion_secreta--> "votando" (prediccion_registrada; no-lectores: botones 1/2)
            --último voto--> "resuelta" (resultado_ronda: revelación + puntos)
            --siguiente_turno--> turno_actual --> (sin ronda) con nuevo lector
```

`votos_esperados` = jugadores con `conectado=true` excluyendo al lector, evaluado por voto
(puede cambiar a mitad de ronda si alguien se desconecta).

### 1.4 Modelos de datos (formas de respuesta)

- `Usuario { id, username, creado_en }`
- `Opcion { numero: 1|2, texto }` · `Pregunta { id, creado_en, opciones: Opcion[2] }`
- `Jugador { usuario_id, username, orden_turno: number|null, puntos, conectado }`
- `Sala { id, codigo, estado: esperando|en_curso|finalizada, anfitrion_id, turno_actual, creado_en, jugadores[] }` — `jugadores` **no viene ordenado**; `turno_actual` es un contador crudo que crece sin límite.
- `PuntoJugador { usuario_id, username, puntos }`
- `MarcadorFinalEntrada { usuario_id, username, puntos_finales, gano }` — empates → varios `gano=true`.
- `MarcadorHistoricoEntrada { username, puntos_totales, partidas, victorias }`
- `ErrorRespuesta { detalle }`

**Estado derivado obligatorio** (calcular igual que el backend, nunca confiar en suposiciones locales):

```
lector      = jugador cuyo orden_turno === sala.turno_actual % sala.jugadores.length
soyLector   = lector?.usuario_id === miUsuarioId
soyAnfitrion = sala.anfitrion_id === miUsuarioId
```

### 1.5 Reglas y edge cases que la UI debe respetar

- Ocultar acciones inválidas por rol, pero **manejar igualmente el evento `error`** (el backend
  revalida todo).
- `empate`: `acierto` siempre false → mostrar "¡Empate! Nadie puntúa".
- Mazo agotado: `robar_carta` → error "No quedan preguntas disponibles" → sugerir finalizar la
  partida o crear más preguntas.
- Reconexión (§6.5 del backend): al cerrarse el WS (no-4003) → `GET /api/salas/{codigo}` para
  resincronizar y reabrir el WS. **Limitación**: el snapshot REST NO incluye la etapa de la
  ronda activa ni el texto de la pregunta → tras reconectar a mitad de ronda, mostrar panel
  "Ronda en curso…" hasta el siguiente evento (o el anfitrión fuerza `siguiente_turno` si el
  lector cayó).
- Salas `finalizada` están muertas (no se pueden re-iniciar; partida nueva = sala nueva).
- La desconexión del anfitrión no es especial; solo la del lector (anfitrión puede forzar turno).
- Normalizar el código de sala a MAYÚSCULAS antes de enviar.
- **La BD arranca con cero preguntas** → la pantalla de administración de preguntas es
  obligatoria (el juego no funciona sin cartas).
- No existe endpoint para "abandonar" una sala: salir = cerrar el WS (el jugador queda en la
  lista con `conectado=false` y sigue contando para el módulo del lector).

---

## 2. Decisiones de arquitectura (tomadas, no re-litigar)

| Tema | Decisión | Razón |
|---|---|---|
| Bundler | **Vite** (plantilla react-ts) | requisito; CORS del backend ya apunta a :5173 |
| Router | **react-router-dom** (modo librería, `createBrowserRouter`) | 5 rutas, navegación programática tras eventos WS |
| Estado | **Redux Toolkit** con slices + thunks | requisito |
| Cliente REST | **Wrapper `fetch` tipado propio + `createAsyncThunk`** (NO RTK Query) | un solo patrón uniforme para el agente; el error `{detalle}` se normaliza en un único punto; el estado de sala es dirigido por WS, no por caché de queries |
| Cliente WS | **Middleware de Redux** que posee el `WebSocket` y traduce eventos ⇄ acciones | patrón canónico RTK para tiempo real; reducers puros y testeables |
| Idioma del código | Dominio en **español** (`salaSlice`, `robarCarta`, `PaginaLobby`); tecnicismos estándar en inglés (`store`, `hooks`, `middleware`) | consistencia con el backend |
| Estilos | **Tailwind CSS v4** (tokens vía `@theme` en CSS), mobile-first, tema oscuro por defecto | requisito; juego de fiesta nocturno → dark-first |
| Persistencia | `localStorage`: `pqp_usuario_id`, `pqp_username`, `pqp_sala_codigo` (última sala, para reanudar) | identidad sin auth según backend |
| Preparación para auth futura | Toda identidad pasa por el slice `sesion` + un único punto `identidad()` que inyecta `usuario_id` en el cliente HTTP y en la URL del WS | agregar tokens después solo toca `clienteHttp` y `sesion` |
| Testing | **Vitest + React Testing Library**; WS falso inyectable; los tests más valiosos son los reducers del mapeo evento-WS→estado y los selectores derivados | la lógica crítica vive en reducers puros |
| Variables de entorno | `VITE_API_URL` (default `http://localhost:8000`); URL del WS derivada (`http→ws`) | un solo knob |
| Rutas | `/` registro+inicio · `/sala/:codigo` (lobby/juego/podio según `sala.estado`) · `/marcador` · `/preguntas` | el ciclo de vida del WS se ata a una sola ruta de sala |

---

## 3. Estructura de carpetas propuesta

```
client/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── .env.example                  # VITE_API_URL=http://localhost:8000
└── src/
    ├── main.tsx                  # monta store + router
    ├── App.tsx                   # definición de rutas + layout raíz + <Notificaciones/>
    ├── estilos/
    │   └── index.css             # @import tailwind + @theme con tokens de diseño
    ├── tipos/
    │   ├── modelos.ts            # modelos del dominio (§4.1)
    │   ├── api.ts                # bodies/respuestas REST (§4.2)
    │   └── eventosWs.ts          # sobres y payloads WS, uniones discriminadas (§4.3)
    ├── api/
    │   ├── clienteHttp.ts        # fetch tipado, base URL, normaliza {detalle} → ErrorApi
    │   ├── usuariosApi.ts
    │   ├── salasApi.ts           # crear, unirse, obtener, iniciar, finalizar, puntos
    │   ├── preguntasApi.ts
    │   ├── constantesApi.ts
    │   └── marcadorApi.ts
    ├── ws/
    │   ├── clienteWs.ts          # clase ConexionSala: abre/cierra socket, backoff, callbacks
    │   └── wsMiddleware.ts       # traduce acciones ⇄ eventos WS, orquesta reconexión
    ├── store/
    │   ├── index.ts              # configureStore + middleware WS
    │   ├── hooks.ts              # useAppDispatch / useAppSelector tipados
    │   └── slices/
    │       ├── sesionSlice.ts
    │       ├── salaSlice.ts
    │       ├── puntajesSlice.ts
    │       ├── constantesSlice.ts
    │       └── uiSlice.ts
    ├── seleccionadores/
    │   └── juego.ts              # selectLector, selectSoyLector, selectSoyAnfitrion, etc.
    ├── utilidades/
    │   ├── almacenamiento.ts     # get/set/clear tipados de localStorage
    │   └── codigoSala.ts         # normalización a mayúsculas + validación de alfabeto
    ├── componentes/              # compartidos, presentacionales
    │   ├── Boton.tsx
    │   ├── CampoTexto.tsx
    │   ├── TarjetaDilema.tsx
    │   ├── FichaJugador.tsx      # username + punto de conexión + puntos + insignias
    │   ├── Notificaciones.tsx    # toasts globales (lee uiSlice)
    │   ├── PantallaCarga.tsx
    │   └── EstadoVacio.tsx
    ├── paginas/
    │   ├── inicio/
    │   │   ├── PaginaInicio.tsx
    │   │   ├── FormularioRegistro.tsx
    │   │   ├── FormularioUnirse.tsx
    │   │   └── BotonCrearSala.tsx
    │   ├── sala/
    │   │   ├── PaginaSala.tsx          # contenedor de /sala/:codigo
    │   │   ├── useConexionSala.ts      # hook: sync REST + conectar/desconectar WS
    │   │   ├── VistaLobby.tsx
    │   │   ├── VistaJuego.tsx
    │   │   ├── VistaPodio.tsx
    │   │   └── juego/
    │   │       ├── PanelLector.tsx
    │   │       ├── SelectorPrediccion.tsx
    │   │       ├── PanelVotante.tsx
    │   │       ├── ProgresoVotos.tsx
    │   │       ├── PanelResultado.tsx
    │   │       ├── PanelRondaDesconocida.tsx
    │   │       └── MarcadorLateral.tsx
    │   ├── marcador/
    │   │   └── PaginaMarcador.tsx
    │   └── preguntas/
    │       ├── PaginaPreguntas.tsx
    │       ├── FormularioPregunta.tsx
    │       └── TarjetaPreguntaAdmin.tsx
    └── tests/                    # espejo de src; fakes de WS y fetch
```

---

## 4. Tipos TypeScript (conceptuales — nombre + campos, sin implementar)

### 4.1 `tipos/modelos.ts` — dominio (espejo exacto de §1.4)

| Tipo | Campos |
|---|---|
| `Usuario` | `id: string; username: string; creado_en: string` |
| `Opcion` | `numero: 1\|2; texto: string` |
| `Pregunta` | `id: string; creado_en: string; opciones: Opcion[]` |
| `Jugador` | `usuario_id: string; username: string; orden_turno: number\|null; puntos: number; conectado: boolean` |
| `Sala` | `id: string; codigo: string; estado: EstadoSala; anfitrion_id: string; turno_actual: number; creado_en: string; jugadores: Jugador[]` |
| `PuntoJugador` | `usuario_id: string; username: string; puntos: number` |
| `MarcadorFinalEntrada` | `usuario_id: string; username: string; puntos_finales: number; gano: boolean` |
| `MarcadorHistoricoEntrada` | `username: string; puntos_totales: number; partidas: number; victorias: number` |

Uniones literales (valores de cable exactos):
`EstadoSala = 'esperando'|'en_curso'|'finalizada'` ·
`EtapaRonda = 'leyendo'|'votando'|'resuelta'` ·
`PrediccionClave = 'mayoria_1'|'todos_1'|'mayoria_2'|'todos_2'` ·
`ResultadoClave = PrediccionClave | 'empate'` ·
`OpcionVoto = 1|2`.

### 4.2 `tipos/api.ts` — REST

| Tipo | Campos / notas |
|---|---|
| `ErrorRespuesta` | `detalle: string` |
| `ErrorApi` (clase) | `detalle: string; status: number` — lo que lanza `clienteHttp` en cualquier no-2xx |
| `CrearUsuarioBody` | `username: string` |
| `AccionSalaBody` | `usuario_id: string` — sirve para crear/unirse/iniciar/finalizar |
| `FinalizarRespuesta` | `sala: Sala; marcador_final: MarcadorFinalEntrada[]` |
| `CrearPreguntaBody` / `OpcionesPregunta` | `opcion_1: string; opcion_2: string` |
| `ActualizarPuntosBody` | `puntos: number` |
| `PrediccionConstante` | `clave: PrediccionClave; etiqueta: string` |
| `ParametrosPaginacion` | `desplazamiento?: number; limite?: number` |

### 4.3 `tipos/eventosWs.ts` — WebSocket (uniones discriminadas por `evento`)

- `SobreWs<E extends string, D>` = `{ evento: E; datos: D }` — sobre genérico.
- `PreguntaEnRonda` = `{ id: string; opcion_1: string; opcion_2: string }` — **ojo: forma
  distinta al modelo REST `Pregunta`** (strings planos, sin array `opciones`).
- `ResumenJugador` = `{ usuario_id: string; username: string }`.

**Cliente → Servidor** (`EventoCliente`, unión de):
`robar_carta {}` · `prediccion_secreta { prediccion: PrediccionClave }` ·
`voto { opcion: OpcionVoto }` · `siguiente_turno {}`.

**Servidor → Cliente** (`EventoServidor`, unión discriminada de):

| evento | datos |
|---|---|
| `jugador_unido` / `jugador_salio` | `ResumenJugador` |
| `partida_iniciada` | `{ orden: Array<ResumenJugador & {orden_turno: number}>; lector: ResumenJugador }` |
| `turno_actual` | `{ numero: number; lector: ResumenJugador }` |
| `carta_robada` | `{ ronda_id: string; pregunta: PreguntaEnRonda }` |
| `prediccion_registrada` | `{ lector_id: string }` |
| `voto_registrado` | `{ votos_recibidos: number; votos_esperados: number }` |
| `resultado_ronda` | `{ votos: Array<ResumenJugador & {opcion: OpcionVoto}>; resultado: ResultadoClave; prediccion: PrediccionClave; acierto: boolean; puntos_lector: number }` |
| `partida_finalizada` | `{ marcador_final: MarcadorFinalEntrada[] }` |
| `error` | `{ detalle: string }` |

El parser de mensajes entrantes hace `switch` exhaustivo sobre `evento` (con chequeo `never`)
y descarta con warning cualquier evento desconocido.

---

## 5. Diseño de slices de Redux Toolkit

### 5.1 `sesionSlice` (usuario/sesión)

**Estado inicial:**
`{ usuario: Usuario|null, cargando: boolean, error: string|null, restaurada: boolean }`

**Thunks:**
- `crearUsuario(username)` → `POST /api/usuarios`; al éxito persiste `usuario_id`/`username` en
  localStorage. El 409 se muestra inline en el formulario ("Ese nombre ya está en uso").
- `restaurarSesion()` → al arrancar la app: lee `pqp_usuario_id`; si existe,
  `GET /api/usuarios/{id}`; si 404, limpia localStorage. Marca `restaurada=true` al terminar
  (con o sin usuario) para que el router sepa cuándo decidir.

**Reducers:** `cerrarSesion()` (limpia estado + localStorage; útil en desarrollo).

### 5.2 `salaSlice` (sala + juego — el corazón)

**Estado inicial:**

```
{
  sala: Sala | null,
  cargando: boolean,
  error: string | null,              // errores REST de sala (crear/unirse/iniciar/finalizar)
  conexion: 'desconectado'|'conectando'|'conectado'|'reconectando',
  motivoExpulsion: string | null,    // razón del cierre 4003
  ronda: {
    id: string | null,
    etapa: EtapaRonda | null,        // null = sin ronda activa
    pregunta: PreguntaEnRonda | null,
    votosRecibidos: number,
    votosEsperados: number,
    miVoto: OpcionVoto | null,       // solo feedback local de UI
    miPrediccion: PrediccionClave | null,  // solo feedback local del lector
    resultado: DatosResultadoRonda | null, // payload completo de resultado_ronda
    desconocida: boolean             // true si reconecté con estado=en_curso sin saber la etapa
  },
  errorJuego: string | null          // último evento WS `error` (se muestra como toast y se limpia)
}
```

**Thunks REST:** `crearSala()`, `unirseSala(codigo)`, `sincronizarSala(codigo)` (GET — usado al
entrar a la ruta y en cada reconexión), `iniciarPartida()`, `finalizarPartida()`.

**Acciones de intención WS (las intercepta el middleware, no mutan estado por sí solas):**
`conectarWs(codigo)` · `desconectarWs()` · `robarCarta()` · `enviarPrediccion(prediccion)` ·
`enviarVoto(opcion)` · `siguienteTurno()`.

**Reducers para eventos WS entrantes (despachados por el middleware) — mapeo exacto:**

| Acción (← evento WS) | Mutación de estado |
|---|---|
| `wsConectado` | `conexion='conectado'`; `motivoExpulsion=null` |
| `wsReconectando` / `wsDesconectado` | `conexion='reconectando'` / `'desconectado'` |
| `wsExpulsado(motivo)` (cierre 4003) | limpia `sala` y `ronda`; guarda `motivoExpulsion` |
| `jugadorUnido` | marca `conectado=true` en ese jugador; si no está en la lista, lo agrega (`orden_turno=null`, `puntos=0`) |
| `jugadorSalio` | marca `conectado=false` |
| `partidaIniciada` | `sala.estado='en_curso'`; asigna `orden_turno` a cada jugador desde `orden` |
| `turnoActual` | `sala.turno_actual=numero`; **resetea `ronda` completa** (etapa null, sin voto/predicción/resultado, `desconocida=false`) |
| `cartaRobada` | `ronda.id`, `ronda.pregunta`, `etapa='leyendo'`, `desconocida=false` |
| `prediccionRegistrada` | `etapa='votando'` |
| `votoRegistrado` | actualiza `votosRecibidos`/`votosEsperados` |
| `resultadoRonda` | `etapa='resuelta'`; guarda payload en `ronda.resultado`; suma: al jugador lector le fija `puntos = puntos_lector`; `desconocida=false` |
| `partidaFinalizada` | `sala.estado='finalizada'` (el marcador final lo guarda `puntajesSlice`) |
| `errorJuego(detalle)` | `errorJuego=detalle` (+ `limpiarErrorJuego()`); caso especial: si `detalle` es "Ya votaste en esta ronda", conservar `miVoto` |

En `sincronizarSala.fulfilled`: reemplaza `sala`; si `estado='en_curso'` y no hay ronda
conocida → `ronda.desconocida=true` (activa el panel "Ronda en curso…").

Al despachar `enviarVoto` / `enviarPrediccion`, el reducer del propio slice registra
`miVoto`/`miPrediccion` de forma **optimista solo para deshabilitar botones**; si llega
`errorJuego` con 400/409 relevante, se revierte. Nunca se usa para lógica de juego.

### 5.3 `puntajesSlice` (marcadores)

**Estado inicial:**
`{ marcadorFinal: MarcadorFinalEntrada[]|null, historico: MarcadorHistoricoEntrada[], cargandoHistorico: boolean, errorHistorico: string|null }`

**Thunks:** `cargarMarcadorHistorico()` → `GET /api/marcador`.

**Reducers/extraReducers:**
- `partidaFinalizada` (mismo evento WS que consume `salaSlice`) → guarda `marcadorFinal`.
- `finalizarPartida.fulfilled` (respuesta REST del anfitrión) → también guarda `marcadorFinal`
  (idempotente con el evento WS; el anfitrión recibe ambos).
- `limpiarMarcadorFinal()` al salir del podio.

Los puntos EN VIVO no viven aquí: viven en `sala.jugadores[].puntos` (fuente: snapshot REST +
`resultado_ronda`). `MarcadorLateral` los lee con un selector que ordena por puntos.

### 5.4 Slices auxiliares

- `constantesSlice`: `{ predicciones: PrediccionConstante[], cargado: boolean }` + thunk
  `cargarPredicciones()` (`GET /api/constantes/predicciones`). Se carga al montar `PaginaSala`
  (el selector de predicción NUNCA hardcodea etiquetas).
- `uiSlice`: `{ notificaciones: Array<{id, tipo: 'error'|'exito'|'info', mensaje}> }` +
  `notificar()`/`descartar()`. Los `ErrorApi` de thunks y los `errorJuego` WS terminan aquí
  como toasts (salvo los que se muestran inline, como el 409 de username).

### 5.5 Middleware de WebSocket (`ws/wsMiddleware.ts`) — estrategia de sincronización

- Posee la instancia única de `ConexionSala` (clase en `clienteWs.ts`, inyectable para tests).
- **Saliente:** al ver `conectarWs(codigo)` abre
  `ws(s)://<host>/ws/salas/{codigo}?usuario_id=<sesion.usuario.id>`; al ver
  `robarCarta`/`enviarPrediccion`/`enviarVoto`/`siguienteTurno` serializa el sobre
  `{evento, datos}` correspondiente; al ver `desconectarWs` cierra limpio (sin reintento).
- **Entrante:** parsea el sobre, valida contra la unión `EventoServidor` y despacha la acción
  equivalente del slice (tabla §5.2). Un evento desconocido solo loguea warning.
- **Reconexión:** en `close` no-intencional y código ≠ 4003 → backoff exponencial
  1s, 2s, 4s, 8s (tope 10s, reintentos indefinidos mientras la ruta de sala esté activa).
  Antes de cada reapertura despacha `sincronizarSala(codigo)` y espera su resultado (así el
  estado se reconstruye del snapshot REST y luego el WS retoma el flujo de eventos).
- **Expulsión:** `close` con código 4003 → `wsExpulsado(reason)`; sin reintento; `PaginaSala`
  redirige a `/` mostrando el motivo como toast.
- **Reanudación móvil:** listener de `visibilitychange`: al volver a visible con conexión no
  conectada → forzar ciclo resync+reconexión inmediato.

---

## 6. Pantallas y componentes (responsabilidad de cada uno)

Las 4 pantallas base del requisito se amplían con **Podio**, **Marcador histórico** y
**Administración de preguntas** porque el backend las requiere explícitamente (§10 del .md;
la BD arranca sin preguntas y el marcador histórico tiene endpoint propio).

### 6.1 `/` — PaginaInicio (registro + crear/unirse)

| Componente | Responsabilidad |
|---|---|
| `PaginaInicio` | Si `sesion.usuario === null` (tras `restaurarSesion`) muestra registro; si hay usuario, muestra crear/unirse + saludo "Hola, {username}" + enlaces a `/marcador` y `/preguntas`. Si hay `pqp_sala_codigo` guardado y la sala sigue viva, ofrece "Volver a la sala {codigo}". |
| `FormularioRegistro` | Input username con validación local (3–30, sin espacios) + errores 409/422 inline en español. Botón "Crear usuario". |
| `BotonCrearSala` | Despacha `crearSala()`; al éxito navega a `/sala/:codigo`. |
| `FormularioUnirse` | Input de 6 caracteres, fuerza mayúsculas y alfabeto válido mientras se escribe; despacha `unirseSala`; maneja 404 ("Sala no encontrada") y 409 ("La partida ya empezó") inline; al éxito navega a `/sala/:codigo`. |

### 6.2 `/sala/:codigo` — PaginaSala (contenedor)

| Componente | Responsabilidad |
|---|---|
| `PaginaSala` | Guarda de sesión (sin usuario → redirige a `/`). Ejecuta `useConexionSala`. Elige vista por `sala.estado`: `esperando`→Lobby, `en_curso`→Juego, `finalizada`→Podio (con `marcadorFinal` si existe; si se llegó por GET a una sala ya muerta, muestra aviso "Esta partida ya terminó" + enlace al marcador). Muestra barra de estado de conexión ("Reconectando…") cuando `conexion!=='conectado'`. |
| `useConexionSala(codigo)` | Hook: al montar → `unirseSala(codigo)` (idempotente, cubre deep-links) → `sincronizarSala` → `conectarWs`; persiste `pqp_sala_codigo`; al desmontar → `desconectarWs()`. Reacciona a `motivoExpulsion` navegando a `/` con toast. |

### 6.3 VistaLobby

| Componente | Responsabilidad |
|---|---|
| `VistaLobby` | Layout del lobby. |
| `CodigoSala` | Código en tipografía gigante + botón "Copiar código" (clipboard + toast "Copiado"). |
| `ListaJugadores` | Lista de `FichaJugador` (punto verde/gris por `conectado`, corona para el anfitrión). Se actualiza en vivo con `jugadorUnido`/`jugadorSalio`. |
| `BotonIniciar` | Solo visible para el anfitrión. Deshabilitado si hay <2 jugadores conectados (ver §9-D1). Despacha `iniciarPartida()`; errores 403/409 → toast. Los no-anfitriones ven "Esperando a que {anfitrión} inicie la partida…". |

### 6.4 VistaJuego (dirigida por `ronda.etapa` + rol derivado)

| Componente | Responsabilidad |
|---|---|
| `VistaJuego` | Orquesta sub-paneles según `etapa` y `soyLector`. Cabecera: "Turno de {lector.username}" (+ "(tú)" si soy yo) y aviso si el lector está desconectado. |
| `TarjetaDilema` | Carta con Opción 1 vs Opción 2 (colores de acento distintos por opción, tokens §7). Visible para todos desde `carta_robada`. |
| `PanelLector` | Solo lector. Sin ronda: botón "Robar carta" (maneja error "No quedan preguntas disponibles" con toast + sugerencia de finalizar o crear preguntas). Etapa `leyendo`: renderiza `SelectorPrediccion`. Etapa `votando`: "Predicción guardada. Esperando votos…". |
| `SelectorPrediccion` | 4 opciones con `etiqueta` de `constantes.predicciones` (nunca hardcodeadas). Confirmación explícita ("Confirmar predicción") porque es irreversible. |
| `PanelVotante` | Solo no-lectores. Antes de `votando`: "El lector está leyendo la carta…". En `votando`: dos botones grandes (1 ☝️ / 2 ✌️) → `enviarVoto`; tras votar (miVoto) quedan bloqueados con "Voto registrado". |
| `ProgresoVotos` | "Votos: {recibidos}/{esperados}" con barra; visible para todos en `votando`. |
| `PanelResultado` | La revelación de `resultado_ronda`: lista quién votó qué, resultado (con label en español, ej. "La mayoría eligió la Opción 1" / "¡Empate! Nadie puntúa"), predicción del lector, acierto (✅ "+1 punto para {lector}" / ❌ "El lector falló"). Botón "Siguiente turno" (solo lector o anfitrión). |
| `PanelRondaDesconocida` | Cuando `ronda.desconocida`: "Hay una ronda en curso… esperando la próxima jugada". Si soy anfitrión y el lector está desconectado: botón "Forzar siguiente turno". |
| `MarcadorLateral` | Puntos en vivo desde `sala.jugadores` ordenados desc (drawer inferior en móvil, sidebar en ≥md). |
| `BotonFinalizar` | Solo anfitrión, con diálogo de confirmación ("¿Terminar la partida?"). Despacha `finalizarPartida()`. |

### 6.5 VistaPodio

| Componente | Responsabilidad |
|---|---|
| `VistaPodio` | Renderiza `marcadorFinal`: ganador(es) destacados (`gano=true`, soporta empates múltiples: "¡Ganadores!"), resto ordenado por `puntos_finales`. Botones: "Volver al inicio" (limpia sala + `pqp_sala_codigo`) y "Ver marcador histórico". Nota visible: para jugar otra vez se crea una sala nueva. |

### 6.6 `/marcador` — PaginaMarcador

| Componente | Responsabilidad |
|---|---|
| `PaginaMarcador` | Carga `cargarMarcadorHistorico()`; tabla: posición, username, `puntos_totales`, `partidas`, `victorias`; destaca la fila del usuario propio. `EstadoVacio`: "Todavía no hay partidas terminadas". |

### 6.7 `/preguntas` — PaginaPreguntas (administración de cartas)

| Componente | Responsabilidad |
|---|---|
| `PaginaPreguntas` | Lista paginada (`desplazamiento`/`limite`, botón "Cargar más"). `EstadoVacio` con CTA: "No hay cartas todavía. ¡Crea la primera!" (crítico: sin preguntas no hay juego). Estado local del componente o thunks ligeros — esta pantalla no necesita slice propio. |
| `FormularioPregunta` | Dos textareas ("Opción 1" / "Opción 2", no vacías) → `POST /api/preguntas`. Reutilizado para editar (precargado, `PUT .../opciones`). |
| `TarjetaPreguntaAdmin` | Muestra ambas opciones + acciones Editar / Eliminar (confirmación antes del `DELETE`). |

---

## 7. Estilos y tokens de diseño (Tailwind v4, `@theme` en `estilos/index.css`)

**Principios:** mobile-first (el juego se juega con el teléfono en la mano); tema oscuro por
defecto (fiesta); botones de voto enormes y a pulgar; la carta de dilema es la protagonista
visual.

| Token | Valor propuesto | Uso |
|---|---|---|
| `--color-primario` | violeta `#8B5CF6` (escala 50–950) | acciones principales, marca |
| `--color-acento` | fucsia `#EC4899` | momentos de fiesta: revelación, podio |
| `--color-opcion-1` | cian `#22D3EE` | TODO lo relativo a Opción 1 (carta, botón, votos) |
| `--color-opcion-2` | ámbar `#FBBF24` | TODO lo relativo a Opción 2 |
| `--color-exito` / `--color-error` | verde `#34D399` / rojo `#F87171` | acierto/fallo, toasts, conectado/desconectado |
| `--color-fondo` / `--color-superficie` | `#0F0A1E` / `#1E1633` (violeta muy oscuro) | fondo y tarjetas |
| `--font-display` | stack de sistema redondeado (`ui-rounded`, fallback `system-ui`) | código de sala, carta, podio |
| `--font-sans` | `system-ui` stack | resto de la UI (sin fuentes remotas: cero dependencias de red) |

Breakpoints estándar de Tailwind; layout de juego: columna única en móvil con marcador como
drawer inferior; a partir de `md` la carta centra y el marcador pasa a sidebar. Animación de
revelación de `resultado_ronda` con transiciones CSS (sin librerías extra).

---

## 8. Plan de implementación por fases

### Fase 1 — Setup, tipos y cliente HTTP
1. Scaffold Vite (plantilla `react-ts`) en `client/`; instalar `react-router-dom`,
   `@reduxjs/toolkit`, `react-redux`, `tailwindcss` v4 (+ plugin Vite), Vitest + RTL.
   ESLint + Prettier.
2. Crear estructura de carpetas (§3), `estilos/index.css` con tokens (§7), `.env.example`.
3. Escribir TODOS los tipos de §4 (modelos, api, eventosWs).
4. `clienteHttp.ts`: base URL de `VITE_API_URL`, JSON por defecto, no-2xx → `ErrorApi{detalle,status}`
   (con fallback "Error de conexión con el servidor" si no hay body). Módulos `*Api.ts` tipados
   para cada grupo de endpoints de §1.2.
5. `utilidades/`: almacenamiento y normalización de código de sala.

**Criterios:** `npm run build`, `npm run lint` y `npx tsc --noEmit` en verde; tipos cubren el
100 % de los payloads de §1.2–§1.4 sin `any`.

### Fase 2 — Estado global (slices + middleware WS)
1. Implementar los 5 slices (§5.1–§5.4) con thunks y reducers según las tablas de mapeo.
2. `clienteWs.ts` (clase con callbacks, inyectable) + `wsMiddleware.ts` (§5.5) con backoff y
   manejo de 4003. `store/index.ts` + hooks tipados.
3. Selectores derivados (`seleccionadores/juego.ts`): lector por módulo, `soyLector`,
   `soyAnfitrion`, jugadores ordenados por puntos, votantes esperados.
4. Tests unitarios (los más valiosos del proyecto): cada evento WS → mutación esperada
   (tabla §5.2), selector de lector con `turno_actual` mayor que el nº de jugadores,
   secuencia completa de una ronda (robar→predicción→votos→resultado→siguiente turno),
   reconexión (sync fulfilled con `en_curso` → `desconocida=true`).

**Criterios:** `vitest` en verde; una ronda completa simulada con acciones deja el estado
exactamente como se espera; el middleware no reintenta tras 4003 ni tras `desconectarWs`.

### Fase 3 — Pantallas estáticas (datos mock, sin backend)
1. Rutas + layout raíz + `Notificaciones` + guardas de sesión.
2. Todas las páginas y componentes de §6 renderizando desde estados de store precargados
   (fixtures por escenario: lobby con 4 jugadores, etapa leyendo como lector, votando como
   votante, resultado con empate, podio con empate de ganadores, marcador vacío…).
3. Responsive básico móvil→escritorio con los tokens de §7.

**Criterios:** todo el flujo es navegable con datos falsos; cada sub-estado de la ronda es
visible forzando el estado del store; textos 100 % en español.

### Fase 4 — Integración en tiempo real (backend real)
1. Conectar thunks REST reales: registro (409 inline), restaurar sesión, crear/unirse/iniciar/
   finalizar, preguntas CRUD, constantes, marcador.
2. Activar el flujo WS completo: `useConexionSala`, eventos entrantes moviendo la UI,
   acciones del juego salientes, evento `error` → toast.
3. Reconexión y expulsión: resync + reapertura con backoff, panel "Ronda en curso…",
   `visibilitychange`, cierre 4003 → `/` con motivo.
4. Documentar en `client/README.md` el smoke test manual: levantar backend (§8 del .md del
   backend), crear 3+ preguntas en `/preguntas`, abrir 3 pestañas con 3 usuarios, crear sala,
   unirse, iniciar, jugar 2 rondas completas (incluyendo un empate si se puede), matar una
   pestaña a mitad de votación y verificar que la ronda resuelve, reconectar y verificar
   resync, finalizar y ver podio + marcador histórico.

**Criterios:** el smoke test completo pasa contra el backend local; los errores del backend se
ven en español y nunca rompen la UI; cerrar/reabrir la pestaña a mitad de partida recupera la
sala.

### Fase 5 — Pulido
1. Animación de revelación en `PanelResultado`; micro-transiciones en votos y turnos.
2. Estados de carga/vacío/error en todas las pantallas; deshabilitado + spinner en botones
   que disparan red.
3. Accesibilidad: `aria-live` para eventos de juego (votos, resultado), foco gestionado en
   cambios de vista, contraste AA con los tokens, targets táctiles ≥44px.
4. Título de la app, favicon, metadatos; revisión final responsive; README con setup completo.

**Criterios:** build de producción sin warnings; Lighthouse razonable en móvil; revisión visual
de los 3 breakpoints en cada pantalla.

---

## 9. Riesgos y decisiones abiertas

**Decisiones abiertas (aplicar la recomendación si no hay respuesta):**

- **D1 — Mínimo de jugadores para iniciar:** el backend no impone mínimo, pero con 1 jugador
  la ronda no puede resolverse (0 votantes esperados y la resolución se dispara al llegar un
  voto). *Recomendación:* deshabilitar "Iniciar" con <2 jugadores conectados, con hint
  "Se necesitan al menos 2 jugadores". Confirmar si se prefiere ≥3 (más divertido: lector + 2 votantes).
- **D2 — Corrección manual de puntos** (`PUT/DELETE /puntos`): el backend los expone sin
  restricción de rol. *Recomendación:* dejarlos FUERA del MVP de UI (riesgo de toques
  accidentales en el teléfono > beneficio); añadible luego como panel de anfitrión.
- **D3 — `/preguntas` sin protección:** cualquiera puede crear/editar/borrar cartas (no hay
  auth). *Recomendación:* aceptable para MVP de juego local; enlazarla discretamente desde
  Inicio. Revisitar cuando llegue la autenticación.
- **D4 — Seed de preguntas para desarrollo:** *Recomendación:* además de la pantalla admin,
  incluir un script de seed (`scripts/seed-preguntas.ts` con `fetch` a `POST /api/preguntas`,
  ~20 dilemas en español) para no arrancar siempre con la BD vacía.

**Riesgos técnicos (con mitigación ya diseñada):**

- **R1 — Reconexión a mitad de ronda:** el snapshot REST no incluye etapa ni pregunta activa
  (limitación documentada del backend). Mitigado con `ronda.desconocida` + panel de espera +
  botón de forzar turno para el anfitrión. Es una degradación aceptada, no un bug.
- **R2 — Último votante pendiente se desconecta:** el .md garantiza que "un desconectado nunca
  bloquea la ronda", pero el mecanismo descrito evalúa `votos_esperados` por voto recibido.
  **Verificar en Fase 4** qué pasa si el único voto que falta se desconecta (¿resuelve el
  servidor al detectar la desconexión?). Si la ronda queda colgada, la salida de UI ya existe
  (forzar turno del anfitrión cuando el lector cae no aplica aquí → escalar al backend si se confirma).
- **R3 — Jugador que abandona para siempre:** sigue en `jugadores[]` y le tocarán turnos de
  lector (el módulo lo cuenta). La UI lo señala ("El lector está desconectado") y el anfitrión
  puede forzar turno; sin cambio de backend no hay solución mejor.
- **R4 — Pérdida de localStorage:** el username queda ocupado para siempre (unicidad global,
  sin recuperación). La UI del registro debe sugerir elegir otro nombre ante el 409, sin
  bloquear al usuario.
- **R5 — `jugador_unido` de un usuario desconocido** (snapshot desactualizado): el reducer lo
  agrega con valores por defecto; el siguiente `sincronizarSala` (o cualquier resync) corrige
  `puntos`/`orden_turno`.
