from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import obtener_sesion
from app.models.sesion import Sesion
from app.schemas.sesion import SesionCrear, SesionLeer
from app.schemas.usuario import UsuarioLeer
from app.seguridad import sesion_actual
from app.services import sesiones as servicio_sesiones

router = APIRouter(prefix="/api/sesiones", tags=["sesiones"])


@router.post("", response_model=SesionLeer, status_code=status.HTTP_201_CREATED)
async def iniciar_sesion(
    datos: SesionCrear, sesion: AsyncSession = Depends(obtener_sesion)
) -> SesionLeer:
    usuario, sesion_activa = await servicio_sesiones.iniciar_sesion(sesion, datos.username)
    return SesionLeer(token=sesion_activa.id, usuario=UsuarioLeer.model_validate(usuario))


@router.delete("/actual", status_code=status.HTTP_204_NO_CONTENT)
async def cerrar_sesion(
    sesion_activa: Sesion = Depends(sesion_actual),
    sesion: AsyncSession = Depends(obtener_sesion),
) -> None:
    await servicio_sesiones.cerrar_sesion(sesion, sesion_activa)
