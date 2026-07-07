from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from httpx_ws import WebSocketDisconnect, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport


@asynccontextmanager
async def _conectar(app: FastAPI, codigo: str, usuario_id: str):
    transport = ASGIWebSocketTransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with aconnect_ws(f"/ws/salas/{codigo}?usuario_id={usuario_id}", client) as ws:
            yield ws


async def _crear_usuario(client: AsyncClient, username: str) -> str:
    respuesta = await client.post("/api/usuarios", json={"username": username})
    return respuesta.json()["id"]


async def test_dos_clientes_ven_union_y_salida(client: AsyncClient, app_prueba: FastAPI) -> None:
    anfitrion_id = await _crear_usuario(client, "anfitrion")
    jugador_id = await _crear_usuario(client, "jugador2")
    creada = await client.post("/api/salas", json={"usuario_id": anfitrion_id})
    codigo = creada.json()["codigo"]
    await client.post(f"/api/salas/{codigo}/unirse", json={"usuario_id": jugador_id})

    async with _conectar(app_prueba, codigo, anfitrion_id) as ws_anfitrion:
        async with _conectar(app_prueba, codigo, jugador_id):
            mensaje = await ws_anfitrion.receive_json()
            assert mensaje == {
                "evento": "jugador_unido",
                "datos": {"usuario_id": jugador_id, "username": "jugador2"},
            }

        mensaje_salida = await ws_anfitrion.receive_json()
        assert mensaje_salida == {
            "evento": "jugador_salio",
            "datos": {"usuario_id": jugador_id, "username": "jugador2"},
        }


async def test_sala_distinta_no_recibe_eventos(client: AsyncClient, app_prueba: FastAPI) -> None:
    anfitrion_a_id = await _crear_usuario(client, "anfitrionA")
    jugador_a_id = await _crear_usuario(client, "jugadorA2")
    anfitrion_b_id = await _crear_usuario(client, "anfitrionB")

    creada_a = await client.post("/api/salas", json={"usuario_id": anfitrion_a_id})
    codigo_a = creada_a.json()["codigo"]
    await client.post(f"/api/salas/{codigo_a}/unirse", json={"usuario_id": jugador_a_id})

    creada_b = await client.post("/api/salas", json={"usuario_id": anfitrion_b_id})
    codigo_b = creada_b.json()["codigo"]

    async with _conectar(app_prueba, codigo_b, anfitrion_b_id) as ws_sala_b:
        async with _conectar(app_prueba, codigo_a, jugador_a_id):
            pass

        with pytest.raises(TimeoutError):
            await ws_sala_b.receive_json(timeout=0.2)


async def test_rechaza_conexion_sala_no_encontrada(client: AsyncClient, app_prueba: FastAPI) -> None:
    usuario_id = await _crear_usuario(client, "solitario")

    async with _conectar(app_prueba, "ABCDEF", usuario_id) as ws:
        with pytest.raises(WebSocketDisconnect) as info:
            await ws.receive_json()
        assert info.value.code == 4003


async def test_rechaza_conexion_no_es_miembro(client: AsyncClient, app_prueba: FastAPI) -> None:
    anfitrion_id = await _crear_usuario(client, "anfitrion3")
    intruso_id = await _crear_usuario(client, "intruso")
    creada = await client.post("/api/salas", json={"usuario_id": anfitrion_id})
    codigo = creada.json()["codigo"]

    async with _conectar(app_prueba, codigo, intruso_id) as ws:
        with pytest.raises(WebSocketDisconnect) as info:
            await ws.receive_json()
        assert info.value.code == 4003
