from fastapi import APIRouter

from app.constants import ETIQUETAS_PREDICCION
from app.schemas.constantes import PrediccionConstante

router = APIRouter(prefix="/api/constantes", tags=["constantes"])


@router.get("/predicciones", response_model=list[PrediccionConstante])
async def listar_predicciones() -> list[PrediccionConstante]:
    return [
        PrediccionConstante(clave=clave.value, etiqueta=etiqueta)
        for clave, etiqueta in ETIQUETAS_PREDICCION.items()
    ]
