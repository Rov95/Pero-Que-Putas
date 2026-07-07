from httpx import AsyncClient


async def test_salud(client: AsyncClient) -> None:
    respuesta = await client.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}
