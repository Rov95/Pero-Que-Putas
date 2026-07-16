# Pero Qué Putas — Frontend

Cliente web (React + TypeScript + Vite + Redux Toolkit + Tailwind CSS v4) para el juego de
fiesta "Pero Qué Putas". Tiempo real vía WebSockets contra el backend en
`~/Desktop/Portfolio/Pero-Que-Putas/server`.

## Requisitos

- Node 20+
- El backend corriendo en `http://localhost:8000` (ver `server/README` / `server/.env.example`;
  necesita Postgres).

## Setup

```bash
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000 (default)
npm run dev            # http://localhost:5173
```

Scripts disponibles: `npm run build`, `npm run lint`, `npm test` (Vitest), `npm run format`
(Prettier).

## Modo práctica

Botón **"Modo práctica"** en la pantalla de inicio (junto a "Crear sala"): dispara
`crearPractica` (`POST /api/salas/practica`) y navega directo a `/sala/{codigo}` al
éxito. El backend crea la sala con el usuario actual de anfitrión y 2 bots ya conectados
por WebSocket, así que el lobby llega solo a "3 conectados" y el botón "Iniciar partida"
queda habilitado sin necesitar un segundo humano. A partir de ahí, el cliente no distingue
bots de jugadores humanos — mismo lobby, mismo `VistaJuego`, mismo podio. Si el 409 de
"sin preguntas" llega del backend, se muestra tal cual en un toast. Ver
[`server/README.md`](../server/README.md#modo-práctica) para los detalles del backend
(retrasos configurables, limpieza de tareas, etc).

E2E dedicado: [`e2e/practica.spec.ts`](e2e/practica.spec.ts) (1 solo navegador humano +
2 bots hasta el podio).

## Smoke test manual

1. Levanta el backend (Postgres + `uvicorn app.main:app`).
2. Abre `http://localhost:5173/preguntas` y crea al menos 3-5 preguntas (la BD arranca vacía;
   sin cartas el juego no funciona).
3. Abre 3 pestañas/perfiles distintos (o usa ventanas de incógnito para no compartir
   `localStorage`), registra 3 usuarios distintos.
4. Uno crea una sala, los otros dos se unen con el código de 6 caracteres.
5. El anfitrión inicia la partida (mínimo 2 jugadores conectados).
6. Juega 2+ rondas completas: robar carta → predicción secreta → votar → revelación → siguiente
   turno. Prueba un empate si puedes forzarlo (todos votando distinto).
7. Cierra/recarga una pestaña a mitad de una ronda y reábrela: debe resincronizar sola.
8. El anfitrión finaliza la partida → verifica el podio (soporta empates con varios ganadores)
   y luego el marcador histórico en `/marcador`.

Este flujo se verificó de punta a punta contra un backend real (Postgres vía `pgserver`
embebido) con 3 navegadores headless simulando 3 usuarios simultáneos.

Para probar el flujo completo vos solo (sin abrir 3 pestañas), usa **"Modo práctica"**
desde la pantalla de inicio en vez de los pasos 3-5.

## Limitaciones conocidas del backend (no arreglables solo desde el frontend)

Encontradas durante la verificación end-to-end; documentadas aquí para no perderlas:

- **Reconexión a mitad de ronda activa:** `GET /api/salas/{codigo}` no incluye la etapa de la
  ronda ni la pregunta activa. El frontend lo cubre con el panel "Ronda en curso… esperando la
  próxima jugada" (`ronda.desconocida`), y ofrece ahí mismo "Robar carta" (si sos el lector) y
  "Forzar siguiente turno" (si sos el anfitrión) como acciones de recuperación especulativas —
  el backend las rechaza sin romper nada si no aplican.
- **Voto pendiente que se desconecta sin que llegue otro voto:** `registrar_voto` sólo
  reevalúa `votos_recibidos >= votos_esperados` cuando llega un voto nuevo; una desconexión por
  sí sola no dispara la resolución. Si el único voto que faltaba se desconecta y nadie más vota
  después, la ronda queda colgada. Además, `avanzar_turno` sólo permite forzar el turno si el
  **lector** está desconectado (no si quien falta es un votante), así que en ese caso específico
  no hay forma de destrabarlo desde la UI. Esto está fuera del alcance del frontend — requiere
  un cambio en el backend (p. ej. reevaluar la resolución también al desconectar a un votante
  pendiente).
