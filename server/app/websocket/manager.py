import uuid
from typing import Any

from fastapi import WebSocket


class ConexionesManager:
    def __init__(self) -> None:
        self._conexiones: dict[str, dict[uuid.UUID, WebSocket]] = {}

    async def conectar(self, codigo: str, usuario_id: uuid.UUID, websocket: WebSocket) -> None:
        self._conexiones.setdefault(codigo, {})[usuario_id] = websocket

    def desconectar(self, codigo: str, usuario_id: uuid.UUID) -> None:
        conexiones_sala = self._conexiones.get(codigo)
        if conexiones_sala is None:
            return
        conexiones_sala.pop(usuario_id, None)
        if not conexiones_sala:
            self._conexiones.pop(codigo, None)

    async def enviar_a(self, codigo: str, usuario_id: uuid.UUID, mensaje: dict[str, Any]) -> None:
        websocket = self._conexiones.get(codigo, {}).get(usuario_id)
        if websocket is not None:
            await websocket.send_json(mensaje)

    async def difundir(
        self, codigo: str, mensaje: dict[str, Any], excluir: uuid.UUID | None = None
    ) -> None:
        for usuario_id, websocket in list(self._conexiones.get(codigo, {}).items()):
            if usuario_id == excluir:
                continue
            await websocket.send_json(mensaje)


manager = ConexionesManager()
