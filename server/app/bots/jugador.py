import asyncio
import logging
import random
import time
import uuid
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws import WebSocketDisconnect as WSDesconectado
from httpx_ws.transport import ASGIWebSocketTransport

from app.config import settings

logger = logging.getLogger(__name__)

PREDICCIONES = ["mayoria_1", "todos_1", "mayoria_2", "todos_2"]

# Cuánto esperar como máximo entre dos vueltas del loop antes de revisar de nuevo
# si toca terminar (señal de parada o vida máxima agotada). Terminar SIEMPRE por un
# retorno normal (nunca cancelando la tarea a medio vuelo): cancelar mientras el socket
# in-process está abierto tira abajo la sesión de BD del propio endpoint del servidor
# (comparten el mismo anyio TaskGroup) y corrompe la conexión en el pool.
INTERVALO_SONDEO_SEGUNDOS = 1.0


class BotJugador:
    def __init__(self, app: FastAPI, codigo: str, usuario_id: uuid.UUID, username: str) -> None:
        self._app = app
        self._codigo = codigo
        self._usuario_id = usuario_id
        self._username = username
        self._soy_lector = False
        self._detener = asyncio.Event()

    def detener(self) -> None:
        self._detener.set()

    async def correr(self) -> None:
        try:
            await self._jugar()
        except WSDesconectado:
            pass
        except Exception:
            logger.exception(
                "Error inesperado en el bot %s (sala %s)", self._username, self._codigo
            )

    async def _jugar(self) -> None:
        limite = time.monotonic() + settings.bots_vida_maxima_segundos
        transport = ASGIWebSocketTransport(app=self._app)
        async with AsyncClient(transport=transport, base_url="http://bot") as cliente:
            async with aconnect_ws(
                f"/ws/salas/{self._codigo}?usuario_id={self._usuario_id}", cliente
            ) as ws:
                while True:
                    if self._detener.is_set():
                        return
                    restante = limite - time.monotonic()
                    if restante <= 0:
                        return
                    try:
                        mensaje = await ws.receive_json(
                            timeout=min(restante, INTERVALO_SONDEO_SEGUNDOS)
                        )
                    except TimeoutError:
                        continue
                    evento = mensaje.get("evento")
                    datos = mensaje.get("datos") or {}
                    if await self._reaccionar(ws, evento, datos):
                        return

    async def _retraso_accion(self) -> None:
        espera_ms = random.uniform(settings.bots_retraso_min_ms, settings.bots_retraso_max_ms)
        await asyncio.sleep(espera_ms / 1000)

    async def _retraso_siguiente_turno(self) -> None:
        espera_ms = settings.bots_retraso_siguiente_turno_ms + random.uniform(
            0, settings.bots_retraso_max_ms
        )
        await asyncio.sleep(espera_ms / 1000)

    async def _reaccionar(self, ws: Any, evento: str, datos: dict[str, Any]) -> bool:
        if evento in ("partida_iniciada", "turno_actual"):
            self._soy_lector = datos.get("lector", {}).get("usuario_id") == str(self._usuario_id)
            if self._soy_lector:
                await self._retraso_accion()
                await ws.send_json({"evento": "robar_carta", "datos": {}})
            return False

        if evento == "carta_robada":
            if self._soy_lector:
                await self._retraso_accion()
                prediccion = random.choice(PREDICCIONES)
                await ws.send_json(
                    {"evento": "prediccion_secreta", "datos": {"prediccion": prediccion}}
                )
            return False

        if evento == "prediccion_registrada":
            if not self._soy_lector:
                await self._retraso_accion()
                opcion = random.choice([1, 2])
                await ws.send_json({"evento": "voto", "datos": {"opcion": opcion}})
            return False

        if evento == "voto_registrado":
            return False

        if evento == "resultado_ronda":
            if self._soy_lector:
                await self._retraso_siguiente_turno()
                await ws.send_json({"evento": "siguiente_turno", "datos": {}})
            return False

        if evento == "partida_finalizada":
            return True

        if evento in ("jugador_unido", "jugador_salio"):
            return False

        if evento == "error":
            logger.warning("Bot %s recibió error: %s", self._username, datos.get("detalle"))
            return False

        logger.warning("Bot %s recibió evento desconocido: %s", self._username, evento)
        return False
