import uuid
from typing import Any

EVENTO_JUGADOR_UNIDO = "jugador_unido"
EVENTO_JUGADOR_SALIO = "jugador_salio"
EVENTO_ERROR = "error"


def _sobre(evento: str, datos: dict[str, Any]) -> dict[str, Any]:
    return {"evento": evento, "datos": datos}


def jugador_unido(usuario_id: uuid.UUID, username: str) -> dict[str, Any]:
    return _sobre(EVENTO_JUGADOR_UNIDO, {"usuario_id": str(usuario_id), "username": username})


def jugador_salio(usuario_id: uuid.UUID, username: str) -> dict[str, Any]:
    return _sobre(EVENTO_JUGADOR_SALIO, {"usuario_id": str(usuario_id), "username": username})


def error(detalle: str) -> dict[str, Any]:
    return _sobre(EVENTO_ERROR, {"detalle": detalle})
