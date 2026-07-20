from contextlib import asynccontextmanager
from typing import NamedTuple

from fastapi import FastAPI
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport


class Credenciales(NamedTuple):
    usuario_id: str
    token: str
    cabeceras: dict[str, str]


async def registrar_usuario(client: AsyncClient, username: str) -> Credenciales:
    respuesta = await client.post("/api/usuarios", json={"username": username})
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    token = cuerpo["token"]
    return Credenciales(
        usuario_id=cuerpo["usuario"]["id"],
        token=token,
        cabeceras={"Authorization": f"Bearer {token}"},
    )


@asynccontextmanager
async def conectar_ws(app: FastAPI, codigo: str, token: str):
    transport = ASGIWebSocketTransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with aconnect_ws(f"/ws/salas/{codigo}?token={token}", client) as ws:
            yield ws
