from httpx import AsyncClient

from tests.apoyo import registrar_usuario


async def test_crear_sala(client: AsyncClient) -> None:
    anfitrion = await registrar_usuario(client, "anfitrion")

    respuesta = await client.post("/api/salas", headers=anfitrion.cabeceras)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert len(cuerpo["codigo"]) == 6
    assert cuerpo["estado"] == "esperando"
    assert cuerpo["anfitrion_id"] == anfitrion.usuario_id
    assert len(cuerpo["jugadores"]) == 1
    assert cuerpo["jugadores"][0]["usuario_id"] == anfitrion.usuario_id
    assert cuerpo["jugadores"][0]["username"] == "anfitrion"


async def test_crear_sala_sin_sesion(client: AsyncClient) -> None:
    respuesta = await client.post("/api/salas")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": "No autenticado"}


async def test_unirse_a_sala(client: AsyncClient) -> None:
    anfitrion = await registrar_usuario(client, "anfitrion")
    jugador = await registrar_usuario(client, "jugador2")
    creada = await client.post("/api/salas", headers=anfitrion.cabeceras)
    codigo = creada.json()["codigo"]

    respuesta = await client.post(f"/api/salas/{codigo}/unirse", headers=jugador.cabeceras)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["jugadores"]) == 2
    usernames = {j["username"] for j in cuerpo["jugadores"]}
    assert usernames == {"anfitrion", "jugador2"}


async def test_unirse_a_sala_no_encontrada(client: AsyncClient) -> None:
    jugador = await registrar_usuario(client, "jugador2")
    respuesta = await client.post("/api/salas/ABCDEF/unirse", headers=jugador.cabeceras)
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "Sala no encontrada"}


async def test_unirse_a_sala_ya_empezada(client: AsyncClient) -> None:
    anfitrion = await registrar_usuario(client, "anfitrion")
    jugador = await registrar_usuario(client, "jugador2")
    tardio = await registrar_usuario(client, "jugador3")
    creada = await client.post("/api/salas", headers=anfitrion.cabeceras)
    codigo = creada.json()["codigo"]
    await client.post(f"/api/salas/{codigo}/unirse", headers=jugador.cabeceras)
    await client.post(f"/api/salas/{codigo}/iniciar", headers=anfitrion.cabeceras)

    respuesta = await client.post(f"/api/salas/{codigo}/unirse", headers=tardio.cabeceras)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "La partida ya empezó"}


async def test_consultar_sala(client: AsyncClient) -> None:
    anfitrion = await registrar_usuario(client, "anfitrion")
    creada = await client.post("/api/salas", headers=anfitrion.cabeceras)
    codigo = creada.json()["codigo"]

    respuesta = await client.get(f"/api/salas/{codigo}")
    assert respuesta.status_code == 200
    assert respuesta.json()["codigo"] == codigo


async def test_consultar_sala_no_encontrada(client: AsyncClient) -> None:
    respuesta = await client.get("/api/salas/ABCDEF")
    assert respuesta.status_code == 404


async def test_iniciar_partida(client: AsyncClient) -> None:
    anfitrion = await registrar_usuario(client, "anfitrion")
    jugador = await registrar_usuario(client, "jugador2")
    creada = await client.post("/api/salas", headers=anfitrion.cabeceras)
    codigo = creada.json()["codigo"]
    await client.post(f"/api/salas/{codigo}/unirse", headers=jugador.cabeceras)

    respuesta = await client.post(f"/api/salas/{codigo}/iniciar", headers=anfitrion.cabeceras)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "en_curso"
    ordenes = sorted(j["orden_turno"] for j in cuerpo["jugadores"])
    assert ordenes == [0, 1]


async def test_iniciar_partida_no_anfitrion(client: AsyncClient) -> None:
    anfitrion = await registrar_usuario(client, "anfitrion")
    jugador = await registrar_usuario(client, "jugador2")
    creada = await client.post("/api/salas", headers=anfitrion.cabeceras)
    codigo = creada.json()["codigo"]
    await client.post(f"/api/salas/{codigo}/unirse", headers=jugador.cabeceras)

    respuesta = await client.post(f"/api/salas/{codigo}/iniciar", headers=jugador.cabeceras)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": "Solo el anfitrión puede iniciar la partida"}


async def test_iniciar_partida_ya_en_curso(client: AsyncClient) -> None:
    anfitrion = await registrar_usuario(client, "anfitrion")
    creada = await client.post("/api/salas", headers=anfitrion.cabeceras)
    codigo = creada.json()["codigo"]
    await client.post(f"/api/salas/{codigo}/iniciar", headers=anfitrion.cabeceras)

    respuesta = await client.post(f"/api/salas/{codigo}/iniciar", headers=anfitrion.cabeceras)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "La partida ya empezó"}
