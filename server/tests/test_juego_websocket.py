import asyncio
from contextlib import AsyncExitStack

from fastapi import FastAPI
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from tests.apoyo import registrar_usuario


async def _drenar_jugador_unido(ws) -> None:
    while True:
        try:
            msg = await asyncio.wait_for(ws.receive_json(), timeout=0.5)
        except TimeoutError:
            return
        assert msg["evento"] == "jugador_unido"


async def test_ronda_completa_con_secreto(client: AsyncClient, app_prueba: FastAPI) -> None:
    jugadores = [await registrar_usuario(client, f"jugador{i}") for i in range(4)]
    ids = [j.usuario_id for j in jugadores]
    await client.post(
        "/api/preguntas",
        json={"enunciado": "¿Qué prefieres?", "opcion_1": "Opción 1", "opcion_2": "Opción 2"},
    )
    creada = await client.post("/api/salas", headers=jugadores[0].cabeceras)
    codigo = creada.json()["codigo"]
    for jugador in jugadores[1:]:
        await client.post(f"/api/salas/{codigo}/unirse", headers=jugador.cabeceras)

    async with AsyncExitStack() as stack:
        sockets = {}
        for jugador in jugadores:
            transport = ASGIWebSocketTransport(app=app_prueba)
            ws_client = await stack.enter_async_context(
                AsyncClient(transport=transport, base_url="http://test")
            )
            ws = await stack.enter_async_context(
                aconnect_ws(f"/ws/salas/{codigo}?token={jugador.token}", ws_client)
            )
            sockets[jugador.usuario_id] = ws

        # Drain jugador_unido notifications fired as later sockets connected.
        for uid in ids:
            await _drenar_jugador_unido(sockets[uid])

        iniciada = await client.post(
            f"/api/salas/{codigo}/iniciar", headers=jugadores[0].cabeceras
        )
        assert iniciada.status_code == 200

        lector_id = None
        for uid in ids:
            partida = await sockets[uid].receive_json()
            turno = await sockets[uid].receive_json()
            assert partida["evento"] == "partida_iniciada"
            assert turno["evento"] == "turno_actual"
            lector_id = partida["datos"]["lector"]["usuario_id"]

        votantes = [uid for uid in ids if uid != lector_id]
        assert len(votantes) == 3

        await sockets[lector_id].send_json({"evento": "robar_carta", "datos": {}})
        for uid in ids:
            msg = await sockets[uid].receive_json()
            assert msg["evento"] == "carta_robada"
            assert set(msg["datos"]["pregunta"].keys()) == {
                "id",
                "enunciado",
                "opcion_1",
                "opcion_2",
            }
            assert msg["datos"]["pregunta"]["enunciado"] == "¿Qué prefieres?"

        await sockets[lector_id].send_json(
            {"evento": "prediccion_secreta", "datos": {"prediccion": "mayoria_1"}}
        )
        for uid in ids:
            msg = await sockets[uid].receive_json()
            assert msg["evento"] == "prediccion_registrada"
            assert set(msg["datos"].keys()) == {"lector_id"}

        opciones_por_voto = {votantes[0]: 1, votantes[1]: 1, votantes[2]: 2}
        for i, votante in enumerate(votantes):
            await sockets[votante].send_json(
                {"evento": "voto", "datos": {"opcion": opciones_por_voto[votante]}}
            )
            for uid in ids:
                msg = await sockets[uid].receive_json()
                assert msg["evento"] == "voto_registrado"
                assert set(msg["datos"].keys()) == {"votos_recibidos", "votos_esperados"}
                assert msg["datos"]["votos_recibidos"] == i + 1
                assert msg["datos"]["votos_esperados"] == 3

        resultados = {}
        for uid in ids:
            msg = await sockets[uid].receive_json()
            assert msg["evento"] == "resultado_ronda"
            resultados[uid] = msg["datos"]

        for uid in ids:
            datos = resultados[uid]
            assert datos["resultado"] == "mayoria_1"
            assert datos["prediccion"] == "mayoria_1"
            assert datos["acierto"] is True
            assert datos["puntos_lector"] == 1
            votos_por_usuario = {v["usuario_id"]: v["opcion"] for v in datos["votos"]}
            assert votos_por_usuario == {
                votantes[0]: 1,
                votantes[1]: 1,
                votantes[2]: 2,
            }
