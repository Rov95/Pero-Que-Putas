import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ronda import Ronda
from app.models.sala import Sala
from app.models.usuario import Usuario


async def test_crear_pregunta(client: AsyncClient) -> None:
    respuesta = await client.post(
        "/api/preguntas",
        json={
            "enunciado": "¿Qué prefieres hacer un lunes?",
            "opcion_1": "Comer sopa fría",
            "opcion_2": "Bañarte con agua helada",
        },
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["enunciado"] == "¿Qué prefieres hacer un lunes?"
    assert len(cuerpo["opciones"]) == 2
    assert cuerpo["opciones"][0]["numero"] == 1
    assert cuerpo["opciones"][0]["texto"] == "Comer sopa fría"
    assert cuerpo["opciones"][1]["numero"] == 2
    assert cuerpo["opciones"][1]["texto"] == "Bañarte con agua helada"


async def test_crear_pregunta_sin_enunciado_falla(client: AsyncClient) -> None:
    sin_enunciado = await client.post(
        "/api/preguntas", json={"opcion_1": "A1", "opcion_2": "A2"}
    )
    assert sin_enunciado.status_code == 422

    enunciado_vacio = await client.post(
        "/api/preguntas", json={"enunciado": "", "opcion_1": "A1", "opcion_2": "A2"}
    )
    assert enunciado_vacio.status_code == 422


async def test_listar_preguntas_incluye_opciones(client: AsyncClient) -> None:
    await client.post(
        "/api/preguntas", json={"enunciado": "¿A o B?", "opcion_1": "A1", "opcion_2": "A2"}
    )
    await client.post(
        "/api/preguntas", json={"enunciado": "¿B o C?", "opcion_1": "B1", "opcion_2": "B2"}
    )

    respuesta = await client.get("/api/preguntas")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 2
    assert all(len(p["opciones"]) == 2 for p in cuerpo)
    assert all(p["enunciado"] for p in cuerpo)


async def test_obtener_pregunta(client: AsyncClient) -> None:
    creada = await client.post(
        "/api/preguntas", json={"enunciado": "¿A o B?", "opcion_1": "A1", "opcion_2": "A2"}
    )
    pregunta_id = creada.json()["id"]

    respuesta = await client.get(f"/api/preguntas/{pregunta_id}")
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == pregunta_id
    assert respuesta.json()["enunciado"] == "¿A o B?"


async def test_obtener_pregunta_no_encontrada(client: AsyncClient) -> None:
    respuesta = await client.get("/api/preguntas/00000000-0000-0000-0000-000000000000")
    assert respuesta.status_code == 404


async def test_actualizar_pregunta(client: AsyncClient) -> None:
    creada = await client.post(
        "/api/preguntas", json={"enunciado": "¿A o B?", "opcion_1": "A1", "opcion_2": "A2"}
    )
    pregunta_id = creada.json()["id"]

    respuesta = await client.put(
        f"/api/preguntas/{pregunta_id}",
        json={"enunciado": "¿Nueva o vieja?", "opcion_1": "Nueva1", "opcion_2": "Nueva2"},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["enunciado"] == "¿Nueva o vieja?"
    assert [o["texto"] for o in cuerpo["opciones"]] == ["Nueva1", "Nueva2"]

    verificacion = await client.get(f"/api/preguntas/{pregunta_id}")
    assert verificacion.json()["enunciado"] == "¿Nueva o vieja?"
    assert [o["texto"] for o in verificacion.json()["opciones"]] == ["Nueva1", "Nueva2"]


async def test_actualizar_pregunta_no_encontrada(client: AsyncClient) -> None:
    respuesta = await client.put(
        "/api/preguntas/00000000-0000-0000-0000-000000000000",
        json={"enunciado": "¿A o B?", "opcion_1": "A1", "opcion_2": "A2"},
    )
    assert respuesta.status_code == 404


async def test_obtener_opciones(client: AsyncClient) -> None:
    creada = await client.post(
        "/api/preguntas", json={"enunciado": "¿A o B?", "opcion_1": "A1", "opcion_2": "A2"}
    )
    pregunta_id = creada.json()["id"]

    respuesta = await client.get(f"/api/preguntas/{pregunta_id}/opciones")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"opcion_1": "A1", "opcion_2": "A2"}


async def test_reemplazar_opciones(client: AsyncClient) -> None:
    creada = await client.post(
        "/api/preguntas", json={"enunciado": "¿A o B?", "opcion_1": "A1", "opcion_2": "A2"}
    )
    pregunta_id = creada.json()["id"]

    respuesta = await client.put(
        f"/api/preguntas/{pregunta_id}/opciones", json={"opcion_1": "Nueva1", "opcion_2": "Nueva2"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"opcion_1": "Nueva1", "opcion_2": "Nueva2"}

    verificacion = await client.get(f"/api/preguntas/{pregunta_id}/opciones")
    assert verificacion.json() == {"opcion_1": "Nueva1", "opcion_2": "Nueva2"}


async def test_eliminar_pregunta_cascada(client: AsyncClient) -> None:
    creada = await client.post(
        "/api/preguntas", json={"enunciado": "¿A o B?", "opcion_1": "A1", "opcion_2": "A2"}
    )
    pregunta_id = creada.json()["id"]

    respuesta = await client.delete(f"/api/preguntas/{pregunta_id}")
    assert respuesta.status_code == 204

    verificacion = await client.get(f"/api/preguntas/{pregunta_id}")
    assert verificacion.status_code == 404


async def test_eliminar_pregunta_jugada_se_marca_eliminada(
    client: AsyncClient, sesion_prueba: AsyncSession
) -> None:
    creada = await client.post(
        "/api/preguntas", json={"enunciado": "¿A o B?", "opcion_1": "A1", "opcion_2": "A2"}
    )
    pregunta_id = uuid.UUID(creada.json()["id"])

    # Simula que la pregunta ya se jugó: una ronda la referencia.
    usuario = Usuario(username="lectora")
    sesion_prueba.add(usuario)
    await sesion_prueba.flush()
    sala = Sala(codigo="BORRAR", anfitrion_id=usuario.id)
    sesion_prueba.add(sala)
    await sesion_prueba.flush()
    sesion_prueba.add(
        Ronda(sala_id=sala.id, numero=1, pregunta_id=pregunta_id, lector_id=usuario.id)
    )
    await sesion_prueba.commit()

    respuesta = await client.delete(f"/api/preguntas/{pregunta_id}")
    assert respuesta.status_code == 204

    # Desaparece del API (detalle y listado)...
    assert (await client.get(f"/api/preguntas/{pregunta_id}")).status_code == 404
    listado = await client.get("/api/preguntas")
    assert all(p["id"] != str(pregunta_id) for p in listado.json())

    # ...pero la ronda que la referencia sigue intacta (borrado suave).
    ronda_bd = await sesion_prueba.scalar(
        select(Ronda).where(Ronda.pregunta_id == pregunta_id)
    )
    assert ronda_bd is not None
