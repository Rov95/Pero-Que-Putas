import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OpcionLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero: int
    texto: str


class OpcionesCrear(BaseModel):
    opcion_1: str = Field(min_length=1)
    opcion_2: str = Field(min_length=1)


class OpcionesLeer(BaseModel):
    opcion_1: str
    opcion_2: str


class PreguntaCrear(OpcionesCrear):
    pass


class PreguntaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    creado_en: datetime
    opciones: list[OpcionLeer]
