from httpx import AsyncClient


async def _crear_usuario(client: AsyncClient, username: str) -> str:
    respuesta = await client.post("/api/usuarios", json={"username": username})
    return respuesta.json()["id"]


async def test_crear_sala(client: AsyncClient) -> None:
    usuario_id = await _crear_usuario(client, "anfitrion")

    respuesta = await client.post("/api/salas", json={"usuario_id": usuario_id})
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert len(cuerpo["codigo"]) == 6
    assert cuerpo["estado"] == "esperando"
    assert cuerpo["anfitrion_id"] == usuario_id
    assert len(cuerpo["jugadores"]) == 1
    assert cuerpo["jugadores"][0]["usuario_id"] == usuario_id
    assert cuerpo["jugadores"][0]["username"] == "anfitrion"


async def test_crear_sala_usuario_no_encontrado(client: AsyncClient) -> None:
    respuesta = await client.post(
        "/api/salas", json={"usuario_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "Usuario no encontrado"}


async def test_unirse_a_sala(client: AsyncClient) -> None:
    anfitrion_id = await _crear_usuario(client, "anfitrion")
    jugador_id = await _crear_usuario(client, "jugador2")
    creada = await client.post("/api/salas", json={"usuario_id": anfitrion_id})
    codigo = creada.json()["codigo"]

    respuesta = await client.post(f"/api/salas/{codigo}/unirse", json={"usuario_id": jugador_id})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["jugadores"]) == 2
    usernames = {j["username"] for j in cuerpo["jugadores"]}
    assert usernames == {"anfitrion", "jugador2"}


async def test_unirse_a_sala_no_encontrada(client: AsyncClient) -> None:
    jugador_id = await _crear_usuario(client, "jugador2")
    respuesta = await client.post("/api/salas/ABCDEF/unirse", json={"usuario_id": jugador_id})
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "Sala no encontrada"}


async def test_unirse_a_sala_ya_empezada(client: AsyncClient) -> None:
    anfitrion_id = await _crear_usuario(client, "anfitrion")
    jugador_id = await _crear_usuario(client, "jugador2")
    tardio_id = await _crear_usuario(client, "jugador3")
    creada = await client.post("/api/salas", json={"usuario_id": anfitrion_id})
    codigo = creada.json()["codigo"]
    await client.post(f"/api/salas/{codigo}/unirse", json={"usuario_id": jugador_id})
    await client.post(f"/api/salas/{codigo}/iniciar", json={"usuario_id": anfitrion_id})

    respuesta = await client.post(f"/api/salas/{codigo}/unirse", json={"usuario_id": tardio_id})
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "La partida ya empezó"}


async def test_consultar_sala(client: AsyncClient) -> None:
    anfitrion_id = await _crear_usuario(client, "anfitrion")
    creada = await client.post("/api/salas", json={"usuario_id": anfitrion_id})
    codigo = creada.json()["codigo"]

    respuesta = await client.get(f"/api/salas/{codigo}")
    assert respuesta.status_code == 200
    assert respuesta.json()["codigo"] == codigo


async def test_consultar_sala_no_encontrada(client: AsyncClient) -> None:
    respuesta = await client.get("/api/salas/ABCDEF")
    assert respuesta.status_code == 404


async def test_iniciar_partida(client: AsyncClient) -> None:
    anfitrion_id = await _crear_usuario(client, "anfitrion")
    jugador_id = await _crear_usuario(client, "jugador2")
    creada = await client.post("/api/salas", json={"usuario_id": anfitrion_id})
    codigo = creada.json()["codigo"]
    await client.post(f"/api/salas/{codigo}/unirse", json={"usuario_id": jugador_id})

    respuesta = await client.post(f"/api/salas/{codigo}/iniciar", json={"usuario_id": anfitrion_id})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "en_curso"
    ordenes = sorted(j["orden_turno"] for j in cuerpo["jugadores"])
    assert ordenes == [0, 1]


async def test_iniciar_partida_no_anfitrion(client: AsyncClient) -> None:
    anfitrion_id = await _crear_usuario(client, "anfitrion")
    jugador_id = await _crear_usuario(client, "jugador2")
    creada = await client.post("/api/salas", json={"usuario_id": anfitrion_id})
    codigo = creada.json()["codigo"]
    await client.post(f"/api/salas/{codigo}/unirse", json={"usuario_id": jugador_id})

    respuesta = await client.post(f"/api/salas/{codigo}/iniciar", json={"usuario_id": jugador_id})
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": "Solo el anfitrión puede iniciar la partida"}


async def test_iniciar_partida_ya_en_curso(client: AsyncClient) -> None:
    anfitrion_id = await _crear_usuario(client, "anfitrion")
    creada = await client.post("/api/salas", json={"usuario_id": anfitrion_id})
    codigo = creada.json()["codigo"]
    await client.post(f"/api/salas/{codigo}/iniciar", json={"usuario_id": anfitrion_id})

    respuesta = await client.post(f"/api/salas/{codigo}/iniciar", json={"usuario_id": anfitrion_id})
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "La partida ya empezó"}
