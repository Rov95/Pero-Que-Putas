from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from app.bots.registro import registro as registro_bots
from app.config import settings
from app.errores import ErrorAplicacion
from app.manejadores import (
    manejar_error_aplicacion,
    manejar_error_generico,
    manejar_error_integridad,
    manejar_error_validacion,
)
from app.routers import constantes, preguntas, puntos, salas, sesiones, usuarios
from app.websocket.router import router as websocket_router

api_router = APIRouter(prefix="/api")


@api_router.get("/salud")
async def salud() -> dict[str, str]:
    return {"estado": "ok"}


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    yield
    await registro_bots.detener_todos()


def create_app() -> FastAPI:
    app = FastAPI(title="Pero Qué Putas", lifespan=_ciclo_de_vida)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(ErrorAplicacion, manejar_error_aplicacion)
    app.add_exception_handler(RequestValidationError, manejar_error_validacion)
    app.add_exception_handler(IntegrityError, manejar_error_integridad)
    app.add_exception_handler(Exception, manejar_error_generico)

    app.include_router(api_router)
    app.include_router(usuarios.router)
    app.include_router(sesiones.router)
    app.include_router(preguntas.router)
    app.include_router(constantes.router)
    app.include_router(salas.router)
    app.include_router(puntos.router)
    app.include_router(websocket_router)

    return app


app = create_app()
