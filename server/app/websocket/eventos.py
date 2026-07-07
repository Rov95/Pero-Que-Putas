import uuid
from typing import Any

EVENTO_JUGADOR_UNIDO = "jugador_unido"
EVENTO_JUGADOR_SALIO = "jugador_salio"
EVENTO_ERROR = "error"
EVENTO_PARTIDA_INICIADA = "partida_iniciada"
EVENTO_TURNO_ACTUAL = "turno_actual"
EVENTO_CARTA_ROBADA = "carta_robada"
EVENTO_PREDICCION_REGISTRADA = "prediccion_registrada"
EVENTO_VOTO_REGISTRADO = "voto_registrado"
EVENTO_RESULTADO_RONDA = "resultado_ronda"
EVENTO_PARTIDA_FINALIZADA = "partida_finalizada"


def _sobre(evento: str, datos: dict[str, Any]) -> dict[str, Any]:
    return {"evento": evento, "datos": datos}


def jugador_unido(usuario_id: uuid.UUID, username: str) -> dict[str, Any]:
    return _sobre(EVENTO_JUGADOR_UNIDO, {"usuario_id": str(usuario_id), "username": username})


def jugador_salio(usuario_id: uuid.UUID, username: str) -> dict[str, Any]:
    return _sobre(EVENTO_JUGADOR_SALIO, {"usuario_id": str(usuario_id), "username": username})


def error(detalle: str) -> dict[str, Any]:
    return _sobre(EVENTO_ERROR, {"detalle": detalle})


def partida_iniciada(orden: list[dict[str, Any]], lector: dict[str, Any]) -> dict[str, Any]:
    return _sobre(EVENTO_PARTIDA_INICIADA, {"orden": orden, "lector": lector})


def turno_actual(numero: int, lector: dict[str, Any]) -> dict[str, Any]:
    return _sobre(EVENTO_TURNO_ACTUAL, {"numero": numero, "lector": lector})


def carta_robada(ronda_id: uuid.UUID, pregunta: dict[str, Any]) -> dict[str, Any]:
    return _sobre(EVENTO_CARTA_ROBADA, {"ronda_id": str(ronda_id), "pregunta": pregunta})


def prediccion_registrada(lector_id: uuid.UUID) -> dict[str, Any]:
    return _sobre(EVENTO_PREDICCION_REGISTRADA, {"lector_id": str(lector_id)})


def voto_registrado(votos_recibidos: int, votos_esperados: int) -> dict[str, Any]:
    return _sobre(
        EVENTO_VOTO_REGISTRADO,
        {"votos_recibidos": votos_recibidos, "votos_esperados": votos_esperados},
    )


def resultado_ronda(
    votos: list[dict[str, Any]],
    resultado: str,
    prediccion: str,
    acierto: bool,
    puntos_lector: int,
) -> dict[str, Any]:
    return _sobre(
        EVENTO_RESULTADO_RONDA,
        {
            "votos": votos,
            "resultado": resultado,
            "prediccion": prediccion,
            "acierto": acierto,
            "puntos_lector": puntos_lector,
        },
    )


def partida_finalizada(marcador_final: list[dict[str, Any]]) -> dict[str, Any]:
    return _sobre(EVENTO_PARTIDA_FINALIZADA, {"marcador_final": marcador_final})
