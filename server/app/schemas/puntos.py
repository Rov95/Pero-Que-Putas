import uuid

from pydantic import BaseModel


class PuntoJugador(BaseModel):
    usuario_id: uuid.UUID
    username: str
    puntos: int


class PuntoEstablecer(BaseModel):
    puntos: int


class MarcadorFinalEntrada(BaseModel):
    usuario_id: uuid.UUID
    username: str
    puntos_finales: int
    gano: bool


class MarcadorHistoricoEntrada(BaseModel):
    username: str
    puntos_totales: int
    partidas: int
    victorias: int
