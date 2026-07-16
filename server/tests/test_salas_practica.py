import re

from httpx import AsyncClient


async def _crear_usuario(client: AsyncClient, username: str) -> str:
    respuesta = await client.post("/api/usuarios", json={"username": username})
    return respuesta.json()["id"]


async def _crear_pregunta(client: AsyncClient) -> None:
    await client.post(
        "/api/preguntas", json={"opcion_1": "Pizza con piña", "opcion_2": "Pizza sin piña"}
    )


async def test_crear_sala_practica(client: AsyncClient) -> None:
    await _crear_pregunta(client)
    usuario_id = await _crear_usuario(client, "humano")

    respuesta = await client.post("/api/salas/practica", json={"usuario_id": usuario_id})
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "esperando"
    assert cuerpo["anfitrion_id"] == usuario_id
    assert len(cuerpo["jugadores"]) == 3

    humano = next(j for j in cuerpo["jugadores"] if j["usuario_id"] == usuario_id)
    assert humano["username"] == "humano"

    bots = [j for j in cuerpo["jugadores"] if j["usuario_id"] != usuario_id]
    assert len(bots) == 2
    for bot in bots:
        assert bot["username"].startswith("Bot-")
        assert re.fullmatch(r"\S+", bot["username"])
    assert len({bot["username"] for bot in bots}) == 2


async def test_crear_sala_practica_bots_existen_como_usuarios(client: AsyncClient) -> None:
    await _crear_pregunta(client)
    usuario_id = await _crear_usuario(client, "humano2")

    creada = await client.post("/api/salas/practica", json={"usuario_id": usuario_id})
    cuerpo = creada.json()
    bots = [j for j in cuerpo["jugadores"] if j["usuario_id"] != usuario_id]

    for bot in bots:
        respuesta = await client.get(f"/api/usuarios/{bot['usuario_id']}")
        assert respuesta.status_code == 200
        assert respuesta.json()["username"] == bot["username"]


async def test_crear_sala_practica_sin_preguntas(client: AsyncClient) -> None:
    usuario_id = await _crear_usuario(client, "humano3")

    respuesta = await client.post("/api/salas/practica", json={"usuario_id": usuario_id})
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": (
            "No hay preguntas disponibles. Crea algunas en la pantalla de preguntas "
            "antes de practicar."
        )
    }


async def test_crear_sala_practica_usuario_no_encontrado(client: AsyncClient) -> None:
    await _crear_pregunta(client)

    respuesta = await client.post(
        "/api/salas/practica", json={"usuario_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "Usuario no encontrado"}


async def test_dos_practicas_seguidas_no_chocan_por_nombres(client: AsyncClient) -> None:
    await _crear_pregunta(client)
    usuario_1 = await _crear_usuario(client, "humano4")
    usuario_2 = await _crear_usuario(client, "humano5")

    respuesta_1 = await client.post("/api/salas/practica", json={"usuario_id": usuario_1})
    respuesta_2 = await client.post("/api/salas/practica", json={"usuario_id": usuario_2})

    assert respuesta_1.status_code == 201
    assert respuesta_2.status_code == 201

    usernames_1 = {j["username"] for j in respuesta_1.json()["jugadores"]}
    usernames_2 = {j["username"] for j in respuesta_2.json()["jugadores"]}
    assert usernames_1.isdisjoint(usernames_2)
