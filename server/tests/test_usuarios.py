from httpx import AsyncClient


async def test_crear_usuario(client: AsyncClient) -> None:
    respuesta = await client.post("/api/usuarios", json={"username": "andres"})
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["username"] == "andres"
    assert "id" in cuerpo
    assert "creado_en" in cuerpo


async def test_crear_usuario_duplicado(client: AsyncClient) -> None:
    await client.post("/api/usuarios", json={"username": "andres"})
    respuesta = await client.post("/api/usuarios", json={"username": "andres"})
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "Ese nombre ya está en uso"}


async def test_crear_usuario_duplicado_case_insensitive(client: AsyncClient) -> None:
    await client.post("/api/usuarios", json={"username": "andres"})
    respuesta = await client.post("/api/usuarios", json={"username": "ANDRES"})
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "Ese nombre ya está en uso"}


async def test_obtener_usuario(client: AsyncClient) -> None:
    creado = await client.post("/api/usuarios", json={"username": "andres"})
    usuario_id = creado.json()["id"]

    respuesta = await client.get(f"/api/usuarios/{usuario_id}")
    assert respuesta.status_code == 200
    assert respuesta.json()["username"] == "andres"


async def test_obtener_usuario_no_encontrado(client: AsyncClient) -> None:
    respuesta = await client.get("/api/usuarios/00000000-0000-0000-0000-000000000000")
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "Usuario no encontrado"}


async def test_crear_usuario_muy_corto(client: AsyncClient) -> None:
    respuesta = await client.post("/api/usuarios", json={"username": "ab"})
    assert respuesta.status_code == 422


async def test_crear_usuario_con_espacios(client: AsyncClient) -> None:
    respuesta = await client.post("/api/usuarios", json={"username": "an dres"})
    assert respuesta.status_code == 422
