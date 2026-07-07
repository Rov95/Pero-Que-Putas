from httpx import AsyncClient


async def test_listar_predicciones(client: AsyncClient) -> None:
    respuesta = await client.get("/api/constantes/predicciones")
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"clave": "mayoria_1", "etiqueta": "La mayoría elige la Opción 1"},
        {"clave": "todos_1", "etiqueta": "Todos eligen la Opción 1"},
        {"clave": "mayoria_2", "etiqueta": "La mayoría elige la Opción 2"},
        {"clave": "todos_2", "etiqueta": "Todos eligen la Opción 2"},
    ]
