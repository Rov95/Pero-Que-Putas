import enum


class PrediccionEnum(str, enum.Enum):
    MAYORIA_1 = "mayoria_1"
    TODOS_1 = "todos_1"
    MAYORIA_2 = "mayoria_2"
    TODOS_2 = "todos_2"


ETIQUETAS_PREDICCION: dict[PrediccionEnum, str] = {
    PrediccionEnum.MAYORIA_1: "La mayoría elige la Opción 1",
    PrediccionEnum.TODOS_1: "Todos eligen la Opción 1",
    PrediccionEnum.MAYORIA_2: "La mayoría elige la Opción 2",
    PrediccionEnum.TODOS_2: "Todos eligen la Opción 2",
}


class ResultadoEnum(str, enum.Enum):
    MAYORIA_1 = "mayoria_1"
    TODOS_1 = "todos_1"
    MAYORIA_2 = "mayoria_2"
    TODOS_2 = "todos_2"
    EMPATE = "empate"


class EstadoSalaEnum(str, enum.Enum):
    ESPERANDO = "esperando"
    EN_CURSO = "en_curso"
    FINALIZADA = "finalizada"


class EstadoRondaEnum(str, enum.Enum):
    LEYENDO = "leyendo"
    VOTANDO = "votando"
    RESUELTA = "resuelta"
