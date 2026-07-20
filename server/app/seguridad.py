from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import obtener_sesion
from app.errores import ErrorAplicacion
from app.models.sesion import Sesion
from app.models.usuario import Usuario
from app.services import sesiones as servicio_sesiones

esquema_bearer = HTTPBearer(auto_error=False)


async def sesion_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    sesion: AsyncSession = Depends(obtener_sesion),
) -> Sesion:
    if credenciales is None:
        raise ErrorAplicacion("No autenticado", status_code=401)
    _, sesion_activa = await servicio_sesiones.usuario_por_token(sesion, credenciales.credentials)
    return sesion_activa


async def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    sesion: AsyncSession = Depends(obtener_sesion),
) -> Usuario:
    if credenciales is None:
        raise ErrorAplicacion("No autenticado", status_code=401)
    usuario, _ = await servicio_sesiones.usuario_por_token(sesion, credenciales.credentials)
    return usuario
