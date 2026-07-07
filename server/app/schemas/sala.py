import uuid
from datetime import datetime

from pydantic import BaseModel

from app.constants import EstadoSalaEnum


class SalaCrear(BaseModel):
    usuario_id: uuid.UUID


class UnirseSala(BaseModel):
    usuario_id: uuid.UUID


class IniciarSala(BaseModel):
    usuario_id: uuid.UUID


class JugadorLeer(BaseModel):
    usuario_id: uuid.UUID
    username: str
    orden_turno: int | None
    puntos: int
    conectado: bool


class SalaLeer(BaseModel):
    id: uuid.UUID
    codigo: str
    estado: EstadoSalaEnum
    anfitrion_id: uuid.UUID
    turno_actual: int
    creado_en: datetime
    jugadores: list[JugadorLeer]
