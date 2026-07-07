import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import obtener_sesion
from app.schemas.usuario import UsuarioCrear, UsuarioLeer
from app.services import usuarios as servicio_usuarios

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@router.post("", response_model=UsuarioLeer, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    datos: UsuarioCrear, sesion: AsyncSession = Depends(obtener_sesion)
) -> UsuarioLeer:
    usuario = await servicio_usuarios.crear_usuario(sesion, datos.username)
    return UsuarioLeer.model_validate(usuario)


@router.get("/{usuario_id}", response_model=UsuarioLeer)
async def obtener_usuario(
    usuario_id: uuid.UUID, sesion: AsyncSession = Depends(obtener_sesion)
) -> UsuarioLeer:
    usuario = await servicio_usuarios.obtener_usuario(sesion, usuario_id)
    return UsuarioLeer.model_validate(usuario)
