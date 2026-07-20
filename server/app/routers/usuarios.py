import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import obtener_sesion
from app.models.usuario import Usuario
from app.schemas.sesion import SesionLeer
from app.schemas.usuario import UsuarioCrear, UsuarioLeer
from app.seguridad import usuario_actual
from app.services import sesiones as servicio_sesiones
from app.services import usuarios as servicio_usuarios

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@router.post("", response_model=SesionLeer, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    datos: UsuarioCrear, sesion: AsyncSession = Depends(obtener_sesion)
) -> SesionLeer:
    usuario = await servicio_usuarios.crear_usuario(sesion, datos.username)
    sesion_activa = await servicio_sesiones.crear_sesion(sesion, usuario.id)
    return SesionLeer(token=sesion_activa.id, usuario=UsuarioLeer.model_validate(usuario))


@router.get("/actual", response_model=UsuarioLeer)
async def obtener_usuario_actual(usuario: Usuario = Depends(usuario_actual)) -> UsuarioLeer:
    return UsuarioLeer.model_validate(usuario)


@router.get("/{usuario_id}", response_model=UsuarioLeer)
async def obtener_usuario(
    usuario_id: uuid.UUID, sesion: AsyncSession = Depends(obtener_sesion)
) -> UsuarioLeer:
    usuario = await servicio_usuarios.obtener_usuario(sesion, usuario_id)
    return UsuarioLeer.model_validate(usuario)
