# Pero Qué Putas

Juego de fiesta **colombiano** de "¿qué prefieres?" (would-you-rather) para jugar en
tiempo real desde el celular. Los jugadores entran a una **sala** con un código de 6
caracteres; en cada turno un **lector** roba una carta con dos opciones imposibles,
predice en secreto qué votará el grupo, y el resto vota. Si el lector acierta su
predicción, suma un punto. Al final hay podio y un marcador histórico entre partidas.

Monorepo con dos piezas que corren juntas:

| Pieza | Carpeta | Qué es |
|---|---|---|
| **Backend** | [`server/`](server/) | API REST + WebSockets con la lógica del juego |
| **Frontend** | [`client/`](client/) | App web (móvil primero) que la gente usa para jugar |

---

## Stack

**Frontend** — React 19 · TypeScript · Vite · Redux Toolkit · Tailwind CSS v4 ·
react-router-dom. WebSocket gestionado como middleware de Redux (reconexión con backoff,
resync por REST antes de cada reapertura). Tests con Vitest; e2e de navegador con Playwright.

**Backend** — FastAPI · SQLAlchemy 2 (async) · PostgreSQL 16 · Alembic · Pydantic v2 ·
uvicorn. Tiempo real por WebSockets nativos de FastAPI. Tests con pytest, levantando un
Postgres real y efímero vía `pgserver` (sin Docker).

**Tooling** — [`uv`](https://docs.astral.sh/uv/) para el backend (Python 3.12), `npm`
(Node 20+) para el frontend.

```
┌────────────┐   REST  /api/*        ┌───────────┐        ┌──────────────┐
│  Navegador │ ───────────────────▶  │  FastAPI  │ ─────▶ │ PostgreSQL 16│
│  (React)   │ ◀───────────────────  │ (uvicorn) │ ◀───── │              │
│  :5173     │   WebSocket /ws/*     │  :8000    │        └──────────────┘
└────────────┘                       └───────────┘
```

---

## Requisitos

- **[uv](https://docs.astral.sh/uv/)** (maneja Python 3.12 y las dependencias del backend).
  Instalar: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Node 20+** y `npm` (para el frontend).
- **PostgreSQL** — **no hace falta instalar nada**: los scripts de abajo levantan un
  Postgres local con `pgserver` (un binario autocontenido, sin root, sin Docker). Si
  prefieres Docker, hay un `docker-compose.yml` en `server/` (ver
  [`server/README.md`](server/README.md)).

---

## Correr toda la app en local (sin Docker)

Desde la raíz del repo, un solo comando levanta **Postgres + migraciones + backend +
frontend**:

```bash
./scripts/dev.sh
```

Cuando termine de arrancar:

1. Abre **http://localhost:5173**.
2. La base arranca **sin preguntas**, así que primero entra a **http://localhost:5173/preguntas**
   y crea 3–5 dilemas (sin cartas el juego no puede robar).
3. Registra un usuario, crea una sala y comparte el código. Para probar tú solo, abre
   más pestañas en incógnito (así no comparten `localStorage`), únete con el código,
   inicia la partida (mínimo 2 jugadores) y juega.

`Ctrl-C` apaga el backend y el Postgres automáticamente. El backend queda documentado en
**http://localhost:8000/docs** (Swagger).

<details>
<summary>¿Prefieres arrancar cada pieza a mano (o con Docker)?</summary>

Tres terminales. Postgres primero (elige una opción):

```bash
# Opción A — sin Docker (pgserver). Imprime y deja lista la DATABASE_URL:
export DATABASE_URL="$(uv run --project server python scripts/db.py start)"

# Opción B — con Docker:
cd server && docker compose up -d          # usa la DATABASE_URL por defecto de server/.env
```

Backend:

```bash
cd server
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd client
npm install
npm run dev
```

Para apagar el Postgres sin Docker: `uv run --project server python scripts/db.py stop`.
Detalles del backend en [`server/README.md`](server/README.md); del frontend en
[`client/README.md`](client/README.md).

</details>

---

## Modo práctica (jugar solo, contra bots)

No hace falta convencer a nadie para probar el juego: en la pantalla de inicio, el botón
**"Modo práctica"** crea una sala donde vos sos el anfitrión y **2 bots** ya están unidos y
conectados. El lobby, la partida y el podio funcionan exactamente igual que con humanos —
los bots son clientes WebSocket reales, no una simulación aparte.

- Los bots juegan **al azar**: predicción y voto uniformemente aleatorios entre las
  opciones válidas. No son un rival, son una herramienta para probar el flujo completo
  (lobby → rondas → podio) vos solo.
- Tienen pequeños retrasos (con jitter) antes de cada acción para que se sientan
  "humanos" y te dé tiempo de leer — configurables por variables de entorno del backend,
  ver [`server/README.md`](server/README.md#modo-práctica).
- Al finalizar la partida, los bots quedan registrados en el **marcador histórico** igual
  que cualquier jugador (es la opción más simple; es una herramienta de prueba, no hace
  falta filtrarlos).
- Requiere al menos **1 pregunta** creada en `/preguntas` — igual que cualquier partida.

Bajo el capó: `POST /api/salas/practica` crea la sala, une 2 usuarios `Bot-*` y lanza sus
tareas de cliente WebSocket in-process contra la propia app.

---

## Test end-to-end de toda la app

Un solo comando arranca el stack completo y corre **dos partidas completas** (registro →
crear/unirse a la sala → iniciar → robar carta → predicción → votos → revelación →
finalizar → podio → marcador histórico): una con 3 navegadores humanos y otra en **modo
práctica** (1 navegador + 2 bots), y al terminar apaga todo:

```bash
./scripts/e2e.sh
```

Usa el **Chrome del sistema** (canal `chrome` de Playwright), así que **no descarga
navegadores**. Los tests viven en
[`client/e2e/juego-completo.spec.ts`](client/e2e/juego-completo.spec.ts) y
[`client/e2e/practica.spec.ts`](client/e2e/practica.spec.ts).

Si ya tienes el stack corriendo (p. ej. con `./scripts/dev.sh`), puedes correr solo el
test del navegador:

```bash
cd client && npm run test:e2e
```

### Otros tests

```bash
cd server && uv run pytest      # backend (levanta su propio Postgres con pgserver)
cd client && npm test           # frontend (Vitest, unitarios)
```

---

## Estructura del repo

```
Pero-Que-Putas/
├── scripts/
│   ├── db.py       # Postgres local sin Docker (start | url | stop | status) vía pgserver
│   ├── dev.sh      # levanta toda la app (db + migraciones + backend + frontend)
│   └── e2e.sh      # test e2e de toda la app (stack completo + Playwright)
├── server/         # backend FastAPI + PostgreSQL + WebSockets  → server/README.md
├── client/         # frontend React + Vite + Redux              → client/README.md
└── .local/         # datos de Postgres de pgserver (ignorado por git)
```

## Limitación conocida

Si el único votante que falta se desconecta sin votar (y nadie más vota después), la ronda
puede quedar colgada: el backend sólo reevalúa la resolución cuando llega un voto nuevo, y
el "forzar turno" del anfitrión sólo aplica si quien se cae es el **lector**. Está
documentado en [`client/README.md`](client/README.md) y requiere un arreglo del lado del
backend. El resto del flujo (incluida la reconexión a mitad de partida) está cubierto por
el test e2e.
