from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.errores import ErrorAplicacion
from app.routers import constantes, preguntas, usuarios

api_router = APIRouter(prefix="/api")


@api_router.get("/salud")
async def salud() -> dict[str, str]:
    return {"estado": "ok"}


def create_app() -> FastAPI:
    app = FastAPI(title="Pero Qué Putas")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ErrorAplicacion)
    async def manejar_error_aplicacion(request: Request, exc: ErrorAplicacion) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detalle": exc.detalle})

    app.include_router(api_router)
    app.include_router(usuarios.router)
    app.include_router(preguntas.router)
    app.include_router(constantes.router)

    return app


app = create_app()
