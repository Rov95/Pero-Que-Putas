import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UsuarioCrear(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^\S+$")


class UsuarioLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    creado_en: datetime
