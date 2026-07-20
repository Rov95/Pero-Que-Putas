import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from httpx_ws import WebSocketDisconnect

from tests.apoyo import conectar_ws, registrar_usuario


async def test_dos_clientes_ven_union_y_salida(client: AsyncClient, app_prueba: FastAPI) -> None:
    anfitrion = await registrar_usuario(client, "anfitrion")
    jugador = await registrar_usuario(client, "jugador2")
    creada = await client.post("/api/salas", headers=anfitrion.cabeceras)
    codigo = creada.json()["codigo"]
    await client.post(f"/api/salas/{codigo}/unirse", headers=jugador.cabeceras)

    async with conectar_ws(app_prueba, codigo, anfitrion.token) as ws_anfitrion:
        async with conectar_ws(app_prueba, codigo, jugador.token):
            mensaje = await ws_anfitrion.receive_json()
            assert mensaje == {
                "evento": "jugador_unido",
                "datos": {"usuario_id": jugador.usuario_id, "username": "jugador2"},
            }

        mensaje_salida = await ws_anfitrion.receive_json()
        assert mensaje_salida == {
            "evento": "jugador_salio",
            "datos": {"usuario_id": jugador.usuario_id, "username": "jugador2"},
        }


async def test_sala_distinta_no_recibe_eventos(client: AsyncClient, app_prueba: FastAPI) -> None:
    anfitrion_a = await registrar_usuario(client, "anfitrionA")
    jugador_a = await registrar_usuario(client, "jugadorA2")
    anfitrion_b = await registrar_usuario(client, "anfitrionB")

    creada_a = await client.post("/api/salas", headers=anfitrion_a.cabeceras)
    codigo_a = creada_a.json()["codigo"]
    await client.post(f"/api/salas/{codigo_a}/unirse", headers=jugador_a.cabeceras)

    creada_b = await client.post("/api/salas", headers=anfitrion_b.cabeceras)
    codigo_b = creada_b.json()["codigo"]

    async with conectar_ws(app_prueba, codigo_b, anfitrion_b.token) as ws_sala_b:
        async with conectar_ws(app_prueba, codigo_a, jugador_a.token):
            pass

        with pytest.raises(TimeoutError):
            await ws_sala_b.receive_json(timeout=0.2)


async def test_rechaza_conexion_sala_no_encontrada(client: AsyncClient, app_prueba: FastAPI) -> None:
    solitario = await registrar_usuario(client, "solitario")

    async with conectar_ws(app_prueba, "ABCDEF", solitario.token) as ws:
        with pytest.raises(WebSocketDisconnect) as info:
            await ws.receive_json()
        assert info.value.code == 4003


async def test_rechaza_conexion_no_es_miembro(client: AsyncClient, app_prueba: FastAPI) -> None:
    anfitrion = await registrar_usuario(client, "anfitrion3")
    intruso = await registrar_usuario(client, "intruso")
    creada = await client.post("/api/salas", headers=anfitrion.cabeceras)
    codigo = creada.json()["codigo"]

    async with conectar_ws(app_prueba, codigo, intruso.token) as ws:
        with pytest.raises(WebSocketDisconnect) as info:
            await ws.receive_json()
        assert info.value.code == 4003
