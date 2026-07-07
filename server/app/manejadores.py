from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.errores import ErrorAplicacion


async def manejar_error_aplicacion(request: Request, exc: ErrorAplicacion) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detalle": exc.detalle})


async def manejar_error_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    primer_error = exc.errors()[0]
    campo = ".".join(str(parte) for parte in primer_error["loc"] if parte != "body")
    detalle = f"Dato inválido en '{campo}'" if campo else "Datos inválidos"
    return JSONResponse(status_code=422, content={"detalle": detalle})


async def manejar_error_integridad(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409, content={"detalle": "Conflicto de datos: el registro ya existe"}
    )


async def manejar_error_generico(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detalle": "Error interno del servidor"})
