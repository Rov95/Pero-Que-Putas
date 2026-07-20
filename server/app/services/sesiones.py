import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errores import ErrorAplicacion
from app.models.sesion import Sesion
from app.models.usuario import Usuario


async def crear_sesion(sesion: AsyncSession, usuario_id: uuid.UUID) -> Sesion:
    sesion_activa = Sesion(usuario_id=usuario_id)
    sesion.add(sesion_activa)
    await sesion.commit()
    await sesion.refresh(sesion_activa)
    return sesion_activa


async def iniciar_sesion(sesion: AsyncSession, username: str) -> tuple[Usuario, Sesion]:
    usuario = await sesion.scalar(
        select(Usuario).where(func.lower(Usuario.username) == username.lower())
    )
    if usuario is None:
        raise ErrorAplicacion("Usuario no encontrado", status_code=404)

    sesion_activa = await crear_sesion(sesion, usuario.id)
    return usuario, sesion_activa


async def usuario_por_token(sesion: AsyncSession, token: str) -> tuple[Usuario, Sesion]:
    try:
        token_uuid = uuid.UUID(token)
    except (TypeError, ValueError) as exc:
        raise ErrorAplicacion("Sesión inválida", status_code=401) from exc

    sesion_activa = await sesion.get(Sesion, token_uuid)
    if sesion_activa is None:
        raise ErrorAplicacion("Sesión inválida", status_code=401)

    usuario = await sesion.get(Usuario, sesion_activa.usuario_id)
    if usuario is None:
        raise ErrorAplicacion("Sesión inválida", status_code=401)

    return usuario, sesion_activa


async def cerrar_sesion(sesion: AsyncSession, sesion_activa: Sesion) -> None:
    await sesion.delete(sesion_activa)
    await sesion.commit()
