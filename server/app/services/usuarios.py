import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errores import ErrorAplicacion
from app.models.usuario import Usuario


async def crear_usuario(sesion: AsyncSession, username: str) -> Usuario:
    existe = await sesion.scalar(
        select(Usuario).where(func.lower(Usuario.username) == username.lower())
    )
    if existe is not None:
        raise ErrorAplicacion("Ese nombre ya está en uso", status_code=409)

    usuario = Usuario(username=username)
    sesion.add(usuario)
    await sesion.commit()
    await sesion.refresh(usuario)
    return usuario


async def obtener_usuario(sesion: AsyncSession, usuario_id: uuid.UUID) -> Usuario:
    usuario = await sesion.get(Usuario, usuario_id)
    if usuario is None:
        raise ErrorAplicacion("Usuario no encontrado", status_code=404)
    return usuario
