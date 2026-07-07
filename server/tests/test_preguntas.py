from httpx import AsyncClient


async def test_crear_pregunta(client: AsyncClient) -> None:
    respuesta = await client.post(
        "/api/preguntas", json={"opcion_1": "Comer sopa fría", "opcion_2": "Bañarte con agua helada"}
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert len(cuerpo["opciones"]) == 2
    assert cuerpo["opciones"][0]["numero"] == 1
    assert cuerpo["opciones"][0]["texto"] == "Comer sopa fría"
    assert cuerpo["opciones"][1]["numero"] == 2
    assert cuerpo["opciones"][1]["texto"] == "Bañarte con agua helada"


async def test_listar_preguntas_incluye_opciones(client: AsyncClient) -> None:
    await client.post("/api/preguntas", json={"opcion_1": "A1", "opcion_2": "A2"})
    await client.post("/api/preguntas", json={"opcion_1": "B1", "opcion_2": "B2"})

    respuesta = await client.get("/api/preguntas")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 2
    assert all(len(p["opciones"]) == 2 for p in cuerpo)


async def test_obtener_pregunta(client: AsyncClient) -> None:
    creada = await client.post("/api/preguntas", json={"opcion_1": "A1", "opcion_2": "A2"})
    pregunta_id = creada.json()["id"]

    respuesta = await client.get(f"/api/preguntas/{pregunta_id}")
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == pregunta_id


async def test_obtener_pregunta_no_encontrada(client: AsyncClient) -> None:
    respuesta = await client.get("/api/preguntas/00000000-0000-0000-0000-000000000000")
    assert respuesta.status_code == 404


async def test_obtener_opciones(client: AsyncClient) -> None:
    creada = await client.post("/api/preguntas", json={"opcion_1": "A1", "opcion_2": "A2"})
    pregunta_id = creada.json()["id"]

    respuesta = await client.get(f"/api/preguntas/{pregunta_id}/opciones")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"opcion_1": "A1", "opcion_2": "A2"}


async def test_reemplazar_opciones(client: AsyncClient) -> None:
    creada = await client.post("/api/preguntas", json={"opcion_1": "A1", "opcion_2": "A2"})
    pregunta_id = creada.json()["id"]

    respuesta = await client.put(
        f"/api/preguntas/{pregunta_id}/opciones", json={"opcion_1": "Nueva1", "opcion_2": "Nueva2"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"opcion_1": "Nueva1", "opcion_2": "Nueva2"}

    verificacion = await client.get(f"/api/preguntas/{pregunta_id}/opciones")
    assert verificacion.json() == {"opcion_1": "Nueva1", "opcion_2": "Nueva2"}


async def test_eliminar_pregunta_cascada(client: AsyncClient) -> None:
    creada = await client.post("/api/preguntas", json={"opcion_1": "A1", "opcion_2": "A2"})
    pregunta_id = creada.json()["id"]

    respuesta = await client.delete(f"/api/preguntas/{pregunta_id}")
    assert respuesta.status_code == 204

    verificacion = await client.get(f"/api/preguntas/{pregunta_id}")
    assert verificacion.status_code == 404
