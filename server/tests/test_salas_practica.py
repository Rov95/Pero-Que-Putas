import re

from httpx import AsyncClient

from tests.apoyo import registrar_usuario


async def _crear_pregunta(client: AsyncClient) -> None:
    await client.post(
        "/api/preguntas",
        json={
            "enunciado": "¿Cómo prefieres la pizza?",
            "opcion_1": "Pizza con piña",
            "opcion_2": "Pizza sin piña",
        },
    )


async def test_crear_sala_practica(client: AsyncClient) -> None:
    await _crear_pregunta(client)
    humano = await registrar_usuario(client, "humano")

    respuesta = await client.post("/api/salas/practica", headers=humano.cabeceras)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "esperando"
    assert cuerpo["anfitrion_id"] == humano.usuario_id
    assert len(cuerpo["jugadores"]) == 3

    fila_humano = next(j for j in cuerpo["jugadores"] if j["usuario_id"] == humano.usuario_id)
    assert fila_humano["username"] == "humano"

    bots = [j for j in cuerpo["jugadores"] if j["usuario_id"] != humano.usuario_id]
    assert len(bots) == 2
    for bot in bots:
        assert bot["username"].startswith("Bot-")
        assert re.fullmatch(r"\S+", bot["username"])
    assert len({bot["username"] for bot in bots}) == 2


async def test_crear_sala_practica_bots_existen_como_usuarios(client: AsyncClient) -> None:
    await _crear_pregunta(client)
    humano = await registrar_usuario(client, "humano2")

    creada = await client.post("/api/salas/practica", headers=humano.cabeceras)
    cuerpo = creada.json()
    bots = [j for j in cuerpo["jugadores"] if j["usuario_id"] != humano.usuario_id]

    for bot in bots:
        respuesta = await client.get(f"/api/usuarios/{bot['usuario_id']}")
        assert respuesta.status_code == 200
        assert respuesta.json()["username"] == bot["username"]


async def test_crear_sala_practica_sin_preguntas(client: AsyncClient) -> None:
    humano = await registrar_usuario(client, "humano3")

    respuesta = await client.post("/api/salas/practica", headers=humano.cabeceras)
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": (
            "No hay preguntas disponibles. Crea algunas en la pantalla de preguntas "
            "antes de practicar."
        )
    }


async def test_crear_sala_practica_sin_sesion(client: AsyncClient) -> None:
    await _crear_pregunta(client)

    respuesta = await client.post("/api/salas/practica")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": "No autenticado"}


async def test_dos_practicas_seguidas_no_chocan_por_nombres(client: AsyncClient) -> None:
    await _crear_pregunta(client)
    humano_1 = await registrar_usuario(client, "humano4")
    humano_2 = await registrar_usuario(client, "humano5")

    respuesta_1 = await client.post("/api/salas/practica", headers=humano_1.cabeceras)
    respuesta_2 = await client.post("/api/salas/practica", headers=humano_2.cabeceras)

    assert respuesta_1.status_code == 201
    assert respuesta_2.status_code == 201

    usernames_1 = {j["username"] for j in respuesta_1.json()["jugadores"]}
    usernames_2 = {j["username"] for j in respuesta_2.json()["jugadores"]}
    assert usernames_1.isdisjoint(usernames_2)
