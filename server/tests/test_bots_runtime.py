import asyncio
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from app.bots.registro import registro as registro_bots
from app.config import settings as app_settings


@pytest.fixture(autouse=True)
def _retrasos_de_bots_casi_cero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_settings, "bots_retraso_min_ms", 0)
    monkeypatch.setattr(app_settings, "bots_retraso_max_ms", 0)
    monkeypatch.setattr(app_settings, "bots_retraso_siguiente_turno_ms", 0)


async def _crear_usuario(client: AsyncClient, username: str) -> str:
    respuesta = await client.post("/api/usuarios", json={"username": username})
    return respuesta.json()["id"]


async def _crear_pregunta(client: AsyncClient, opcion_1: str, opcion_2: str) -> None:
    await client.post(
        "/api/preguntas",
        json={"enunciado": "¿Qué prefieres?", "opcion_1": opcion_1, "opcion_2": opcion_2},
    )


async def _esperar_hasta(condicion: Callable[[], Awaitable[bool]], mensaje: str) -> None:
    for _ in range(100):
        if await condicion():
            return
        await asyncio.sleep(0.05)
    raise AssertionError(mensaje)


async def _bots_de_sala(client: AsyncClient, codigo: str, humano_id: str) -> list[dict]:
    respuesta = await client.get(f"/api/salas/{codigo}")
    jugadores = respuesta.json()["jugadores"]
    return [j for j in jugadores if j["usuario_id"] != humano_id]


async def _esperar_bots_conectados(client: AsyncClient, codigo: str, humano_id: str) -> None:
    async def _condicion() -> bool:
        bots = await _bots_de_sala(client, codigo, humano_id)
        return len(bots) == 2 and all(b["conectado"] for b in bots)

    await _esperar_hasta(_condicion, "Los bots no quedaron conectados a tiempo")


async def test_bots_de_practica_quedan_conectados(client: AsyncClient) -> None:
    humano_id = await _crear_usuario(client, "practicante1")
    await _crear_pregunta(client, "Playa", "Montaña")

    creada = await client.post("/api/salas/practica", json={"usuario_id": humano_id})
    assert creada.status_code == 201
    cuerpo = creada.json()
    assert len(cuerpo["jugadores"]) == 3
    codigo = cuerpo["codigo"]

    await _esperar_bots_conectados(client, codigo, humano_id)

    await registro_bots.detener_bots(codigo)


async def test_detener_bots_deja_registro_vacio_y_desconecta(client: AsyncClient) -> None:
    humano_id = await _crear_usuario(client, "practicante2")
    await _crear_pregunta(client, "Perros", "Gatos")

    creada = await client.post("/api/salas/practica", json={"usuario_id": humano_id})
    codigo = creada.json()["codigo"]
    await _esperar_bots_conectados(client, codigo, humano_id)
    assert registro_bots.cantidad_activos(codigo) == 2

    await registro_bots.detener_bots(codigo)

    assert registro_bots.cantidad_activos(codigo) == 0

    async def _condicion() -> bool:
        bots = await _bots_de_sala(client, codigo, humano_id)
        return len(bots) == 2 and all(not b["conectado"] for b in bots)

    await _esperar_hasta(_condicion, "Los bots no quedaron desconectados a tiempo")


async def test_ronda_completa_de_practica(client: AsyncClient, app_prueba: FastAPI) -> None:
    humano_id = await _crear_usuario(client, "practicante3")
    await _crear_pregunta(client, "Código limpio", "Código rápido")

    creada = await client.post("/api/salas/practica", json={"usuario_id": humano_id})
    codigo = creada.json()["codigo"]
    await _esperar_bots_conectados(client, codigo, humano_id)

    async with AsyncExitStack() as stack:
        transport = ASGIWebSocketTransport(app=app_prueba)
        ws_client = await stack.enter_async_context(
            AsyncClient(transport=transport, base_url="http://test")
        )
        ws = await stack.enter_async_context(
            aconnect_ws(f"/ws/salas/{codigo}?usuario_id={humano_id}", ws_client)
        )

        iniciada = await client.post(
            f"/api/salas/{codigo}/iniciar", json={"usuario_id": humano_id}
        )
        assert iniciada.status_code == 200

        partida = await asyncio.wait_for(ws.receive_json(), timeout=5)
        assert partida["evento"] == "partida_iniciada"
        turno = await asyncio.wait_for(ws.receive_json(), timeout=5)
        assert turno["evento"] == "turno_actual"
        lector_id = partida["datos"]["lector"]["usuario_id"]

        if lector_id == humano_id:
            await ws.send_json({"evento": "robar_carta", "datos": {}})
            carta = await asyncio.wait_for(ws.receive_json(), timeout=5)
            assert carta["evento"] == "carta_robada"

            await ws.send_json(
                {"evento": "prediccion_secreta", "datos": {"prediccion": "mayoria_1"}}
            )
            prediccion = await asyncio.wait_for(ws.receive_json(), timeout=5)
            assert prediccion["evento"] == "prediccion_registrada"

            votos_vistos = 0
            resultado = None
            while resultado is None:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=5)
                if msg["evento"] == "voto_registrado":
                    votos_vistos += 1
                elif msg["evento"] == "resultado_ronda":
                    resultado = msg
            assert votos_vistos == 2
            assert len(resultado["datos"]["votos"]) == 2
        else:
            carta = await asyncio.wait_for(ws.receive_json(), timeout=5)
            assert carta["evento"] == "carta_robada"

            prediccion = await asyncio.wait_for(ws.receive_json(), timeout=5)
            assert prediccion["evento"] == "prediccion_registrada"

            await ws.send_json({"evento": "voto", "datos": {"opcion": 1}})

            resultado = None
            turno_siguiente = None
            while turno_siguiente is None:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=5)
                if msg["evento"] == "resultado_ronda":
                    resultado = msg
                elif msg["evento"] == "turno_actual":
                    turno_siguiente = msg
            assert resultado is not None
            assert turno_siguiente["datos"]["numero"] == 1

    await registro_bots.detener_bots(codigo)
