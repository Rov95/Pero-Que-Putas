from sqlalchemy.exc import IntegrityError

from app.errores import ErrorAplicacion
from app.manejadores import (
    manejar_error_aplicacion,
    manejar_error_generico,
    manejar_error_integridad,
)
from httpx import AsyncClient


async def test_error_validacion_cuerpo_espanol(client: AsyncClient) -> None:
    respuesta = await client.post("/api/usuarios", json={})
    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert list(cuerpo.keys()) == ["detalle"]
    assert "username" in cuerpo["detalle"]


async def test_error_validacion_tipo_incorrecto(client: AsyncClient) -> None:
    respuesta = await client.put(
        "/api/salas/ABCDEF/puntos/00000000-0000-0000-0000-000000000000",
        json={"puntos": "no-es-un-numero"},
    )
    assert respuesta.status_code == 422
    assert list(respuesta.json().keys()) == ["detalle"]


async def test_manejador_error_aplicacion() -> None:
    respuesta = await manejar_error_aplicacion(None, ErrorAplicacion("Mensaje en español", 404))
    assert respuesta.status_code == 404
    assert respuesta.body.decode("utf-8") == '{"detalle":"Mensaje en español"}'


async def test_manejador_error_integridad() -> None:
    respuesta = await manejar_error_integridad(None, IntegrityError("stmt", {}, Exception("x")))
    assert respuesta.status_code == 409
    assert b"detalle" in respuesta.body


async def test_manejador_error_generico() -> None:
    respuesta = await manejar_error_generico(None, RuntimeError("boom"))
    assert respuesta.status_code == 500
    assert b"detalle" in respuesta.body
