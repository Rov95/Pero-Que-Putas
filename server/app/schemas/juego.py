from pydantic import BaseModel, Field

from app.constants import PrediccionEnum


class PrediccionSecretaDatos(BaseModel):
    prediccion: PrediccionEnum


class VotoDatos(BaseModel):
    opcion: int = Field(ge=1, le=2)
