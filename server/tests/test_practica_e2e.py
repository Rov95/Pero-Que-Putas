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
from tests.apoyo import registrar_usuario


@pytest.fixture(autouse=True)
def _retrasos_de_bots_casi_cero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_settings, "bots_retraso_min_ms", 0)
    monkeypatch.setattr(app_settings, "bots_retraso_max_ms", 0)
    monkeypatch.setattr(app_settings, "bots_retraso_siguiente_turno_ms", 0)


@pytest.fixture(autouse=True)
async def _sin_fugas_de_bots():
    yield

    async def _condicion() -> bool:
        return registro_bots.cantidad_activos() == 0

    await _esperar_hasta(_condicion, "Quedaron tareas de bots vivas tras el test")


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


async def _jugar_ronda(ws, humano_id: str, turno_msg: dict) -> dict:
    """Juega una ronda completa a partir de un turno_actual ya recibido.

    Devuelve el turno_actual de la ronda siguiente (llega solo, sea porque el
    humano avanza el turno o porque lo hace el bot lector).
    """
    lector_id = turno_msg["datos"]["lector"]["usuario_id"]

    if lector_id == humano_id:
        await ws.send_json({"evento": "robar_carta", "datos": {}})
        carta = await ws.receive_json(timeout=5)
        assert carta["evento"] == "carta_robada"

        await ws.send_json({"evento": "prediccion_secreta", "datos": {"prediccion": "mayoria_1"}})
        prediccion = await ws.receive_json(timeout=5)
        assert prediccion["evento"] == "prediccion_registrada"

        resultado = None
        votos_vistos = 0
        while resultado is None:
            msg = await ws.receive_json(timeout=5)
            if msg["evento"] == "voto_registrado":
                votos_vistos += 1
            elif msg["evento"] == "resultado_ronda":
                resultado = msg
        assert votos_vistos == 2

        await ws.send_json({"evento": "siguiente_turno", "datos": {}})
        siguiente = await ws.receive_json(timeout=5)
        assert siguiente["evento"] == "turno_actual"
        return siguiente

    carta = await ws.receive_json(timeout=5)
    assert carta["evento"] == "carta_robada"
    prediccion = await ws.receive_json(timeout=5)
    assert prediccion["evento"] == "prediccion_registrada"

    await ws.send_json({"evento": "voto", "datos": {"opcion": 1}})

    siguiente = None
    while siguiente is None:
        msg = await ws.receive_json(timeout=5)
        if msg["evento"] == "turno_actual":
            siguiente = msg
    return siguiente


async def test_partida_completa_de_practica_hasta_marcador(
    client: AsyncClient, app_prueba: FastAPI
) -> None:
    humano = await registrar_usuario(client, "practicante_full")
    humano_id = humano.usuario_id
    for i in range(3):
        await _crear_pregunta(client, f"Opción A{i}", f"Opción B{i}")

    creada = await client.post("/api/salas/practica", headers=humano.cabeceras)
    assert creada.status_code == 201
    codigo = creada.json()["codigo"]
    await _esperar_bots_conectados(client, codigo, humano_id)
    bots = await _bots_de_sala(client, codigo, humano_id)
    ids_bots = {b["usuario_id"] for b in bots}
    nombres_bots = {b["username"] for b in bots}

    async with AsyncExitStack() as stack:
        transport = ASGIWebSocketTransport(app=app_prueba)
        ws_client = await stack.enter_async_context(
            AsyncClient(transport=transport, base_url="http://test")
        )
        ws = await stack.enter_async_context(
            aconnect_ws(f"/ws/salas/{codigo}?token={humano.token}", ws_client)
        )

        iniciada = await client.post(f"/api/salas/{codigo}/iniciar", headers=humano.cabeceras)
        assert iniciada.status_code == 200

        partida = await ws.receive_json(timeout=5)
        assert partida["evento"] == "partida_iniciada"
        turno_msg = await ws.receive_json(timeout=5)
        assert turno_msg["evento"] == "turno_actual"

        lectores_vistos = set()
        for _ in range(3):
            lectores_vistos.add(turno_msg["datos"]["lector"]["usuario_id"])
            turno_msg = await _jugar_ronda(ws, humano_id, turno_msg)

        # Con 3 jugadores y rotación módulo n, 3 rondas garantizan que el humano y
        # los 2 bots hayan sido lector exactamente una vez cada uno.
        assert lectores_vistos == {humano_id} | ids_bots

        finalizada = await client.post(
            f"/api/salas/{codigo}/finalizar", headers=humano.cabeceras
        )
        assert finalizada.status_code == 200
        assert len(finalizada.json()["marcador_final"]) == 3

        fin_msg = await ws.receive_json(timeout=5)
        assert fin_msg["evento"] == "partida_finalizada"
        assert len(fin_msg["datos"]["marcador_final"]) == 3

    marcador = await client.get("/api/marcador")
    assert marcador.status_code == 200
    nombres_marcador = {fila["username"] for fila in marcador.json()}
    assert nombres_marcador == {"practicante_full"} | nombres_bots

    # El registro de bots debe vaciarse solo (cada bot termina su propia tarea al
    # recibir partida_finalizada), sin necesidad de detener_bots manual.
    async def _condicion() -> bool:
        return registro_bots.cantidad_activos(codigo) == 0

    await _esperar_hasta(_condicion, "El registro de bots no quedó vacío solo tras finalizar")


async def test_bots_de_practica_abandonada_expiran_solos(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_settings, "bots_vida_maxima_segundos", 0.3)

    humano = await registrar_usuario(client, "practicante_abandona")
    humano_id = humano.usuario_id
    await _crear_pregunta(client, "Perros", "Gatos")

    creada = await client.post("/api/salas/practica", headers=humano.cabeceras)
    codigo = creada.json()["codigo"]

    # No iniciamos la partida: los bots deben colgar solos al agotar su vida máxima.
    async def _condicion() -> bool:
        return registro_bots.cantidad_activos(codigo) == 0

    await _esperar_hasta(_condicion, "Los bots no expiraron por vida máxima a tiempo")

    bots = await _bots_de_sala(client, codigo, humano_id)
    assert len(bots) == 2
    assert all(not b["conectado"] for b in bots)


async def test_carrera_de_votos_de_bots_resuelve_una_sola_vez(
    client: AsyncClient, app_prueba: FastAPI
) -> None:
    # Preguntas no se agotan por sala: sembramos de una vez un mazo suficiente para que
    # ninguna de las 8 salas (cada una puede necesitar hasta 3 robar_carta) se quede sin
    # cartas — eso dejaría una ronda a medias y produciría fallos ajenos a la carrera.
    for i in range(10):
        await _crear_pregunta(client, f"Playa{i}", f"Montaña{i}")

    for intento in range(8):
        humano = await registrar_usuario(client, f"racer{intento}")
        humano_id = humano.usuario_id

        creada = await client.post("/api/salas/practica", headers=humano.cabeceras)
        codigo = creada.json()["codigo"]
        await _esperar_bots_conectados(client, codigo, humano_id)

        async with AsyncExitStack() as stack:
            transport = ASGIWebSocketTransport(app=app_prueba)
            ws_client = await stack.enter_async_context(
                AsyncClient(transport=transport, base_url="http://test")
            )
            ws = await stack.enter_async_context(
                aconnect_ws(f"/ws/salas/{codigo}?token={humano.token}", ws_client)
            )

            iniciada = await client.post(
                f"/api/salas/{codigo}/iniciar", headers=humano.cabeceras
            )
            assert iniciada.status_code == 200

            await ws.receive_json(timeout=5)  # partida_iniciada
            turno_msg = await ws.receive_json(timeout=5)  # turno_actual

            # La rotación módulo n garantiza que el humano sea lector dentro de las
            # primeras 3 rondas; las rondas ajenas se resuelven solas de paso.
            for _ in range(3):
                if turno_msg["datos"]["lector"]["usuario_id"] == humano_id:
                    break
                turno_msg = await _jugar_ronda(ws, humano_id, turno_msg)
            else:
                raise AssertionError(f"intento {intento}: el humano nunca fue lector")

            await ws.send_json({"evento": "robar_carta", "datos": {}})
            carta = await ws.receive_json(timeout=5)
            assert carta["evento"] == "carta_robada"

            await ws.send_json(
                {"evento": "prediccion_secreta", "datos": {"prediccion": "mayoria_1"}}
            )
            prediccion = await ws.receive_json(timeout=5)
            assert prediccion["evento"] == "prediccion_registrada"

            # Con jitter≈0 los 2 bots votan casi simultáneamente: drenamos hasta el
            # silencio para detectar una eventual doble resolución (riesgo R1, §6).
            votos_vistos = 0
            resultados = []
            while True:
                try:
                    msg = await ws.receive_json(timeout=0.5)
                except TimeoutError:
                    break
                if msg["evento"] == "voto_registrado":
                    votos_vistos += 1
                elif msg["evento"] == "resultado_ronda":
                    resultados.append(msg)
                else:
                    raise AssertionError(f"evento inesperado en la ronda: {msg['evento']}")

            assert votos_vistos == 2, f"intento {intento}: {votos_vistos} votos (se esperaban 2)"
            assert len(resultados) == 1, (
                f"intento {intento}: {len(resultados)} resultado_ronda (se esperaba 1)"
            )
            assert resultados[0]["datos"]["puntos_lector"] in (0, 1)

        await registro_bots.detener_bots(codigo)
