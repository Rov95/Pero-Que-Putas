from pydantic import BaseModel


class PrediccionConstante(BaseModel):
    clave: str
    etiqueta: str
