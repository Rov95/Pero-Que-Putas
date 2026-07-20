import uuid

from pydantic import BaseModel, Field

from app.schemas.usuario import UsuarioLeer


class SesionCrear(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^\S+$")


class SesionLeer(BaseModel):
    token: uuid.UUID
    usuario: UsuarioLeer
