import asyncio
from contextlib import AsyncExitStack

from fastapi import FastAPI
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport


async def _crear_usuario(client: AsyncClient, username: str) -> str:
    respuesta = await client.post("/api/usuarios", json={"username": username})
    return respuesta.json()["id"]


async def _drenar_jugador_unido(ws) -> None:
    while True:
        try:
            msg = await asyncio.wait_for(ws.receive_json(), timeout=0.5)
        except TimeoutError:
            return
        assert msg["evento"] == "jugador_unido"


async def test_partida_completa_de_3_jugadores_hasta_marcador(
    client: AsyncClient, app_prueba: FastAPI
) -> None:
    ids = [await _crear_usuario(client, f"e2e{i}") for i in range(3)]
    await client.post(
        "/api/preguntas",
        json={
            "enunciado": "¿Qué prefieres este fin de semana?",
            "opcion_1": "Bailar toda la noche",
            "opcion_2": "Dormir todo el día",
        },
    )

    creada = await client.post("/api/salas", json={"usuario_id": ids[0]})
    codigo = creada.json()["codigo"]
    for uid in ids[1:]:
        await client.post(f"/api/salas/{codigo}/unirse", json={"usuario_id": uid})

    async with AsyncExitStack() as stack:
        sockets = {}
        for uid in ids:
            transport = ASGIWebSocketTransport(app=app_prueba)
            ws_client = await stack.enter_async_context(
                AsyncClient(transport=transport, base_url="http://test")
            )
            ws = await stack.enter_async_context(
                aconnect_ws(f"/ws/salas/{codigo}?usuario_id={uid}", ws_client)
            )
            sockets[uid] = ws

        for uid in ids:
            await _drenar_jugador_unido(sockets[uid])

        iniciada = await client.post(f"/api/salas/{codigo}/iniciar", json={"usuario_id": ids[0]})
        assert iniciada.status_code == 200

        lector_id = None
        for uid in ids:
            partida = await sockets[uid].receive_json()
            await sockets[uid].receive_json()  # turno_actual
            lector_id = partida["datos"]["lector"]["usuario_id"]

        votantes = [uid for uid in ids if uid != lector_id]
        assert len(votantes) == 2

        await sockets[lector_id].send_json({"evento": "robar_carta", "datos": {}})
        for uid in ids:
            msg = await sockets[uid].receive_json()
            assert msg["evento"] == "carta_robada"

        await sockets[lector_id].send_json(
            {"evento": "prediccion_secreta", "datos": {"prediccion": "todos_1"}}
        )
        for uid in ids:
            msg = await sockets[uid].receive_json()
            assert msg["evento"] == "prediccion_registrada"

        for i, votante in enumerate(votantes):
            await sockets[votante].send_json({"evento": "voto", "datos": {"opcion": 1}})
            for uid in ids:
                msg = await sockets[uid].receive_json()
                assert msg["evento"] == "voto_registrado"

        for uid in ids:
            msg = await sockets[uid].receive_json()
            assert msg["evento"] == "resultado_ronda"
            assert msg["datos"]["resultado"] == "todos_1"
            assert msg["datos"]["acierto"] is True
            assert msg["datos"]["puntos_lector"] == 1

    finalizada = await client.post(f"/api/salas/{codigo}/finalizar", json={"usuario_id": ids[0]})
    assert finalizada.status_code == 200
    cuerpo = finalizada.json()
    assert cuerpo["sala"]["estado"] == "finalizada"
    ganador = next(m for m in cuerpo["marcador_final"] if m["usuario_id"] == lector_id)
    assert ganador["puntos_finales"] == 1
    assert ganador["gano"] is True

    marcador = await client.get("/api/marcador", params={"usuario_id": lector_id})
    assert marcador.status_code == 200
    fila = marcador.json()[0]
    assert fila["puntos_totales"] == 1
    assert fila["partidas"] == 1
    assert fila["victorias"] == 1
