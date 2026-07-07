import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import EstadoSalaEnum, PrediccionEnum
from app.errores import ErrorAplicacion
from app.models.pregunta import Opcion, Pregunta
from app.models.sala import Sala, SalaJugador
from app.models.usuario import Usuario
from app.services import juego as servicio_juego
from app.services import salas as servicio_salas


async def _preparar_sala(
    sesion: AsyncSession, n_voters: int, prefix: str
) -> tuple[Sala, list[uuid.UUID]]:
    usuarios = [Usuario(username=f"{prefix}{i}") for i in range(n_voters + 1)]
    sesion.add_all(usuarios)
    await sesion.flush()

    pregunta = Pregunta()
    pregunta.opciones = [Opcion(numero=1, texto="Opción 1"), Opcion(numero=2, texto="Opción 2")]
    sesion.add(pregunta)

    codigo = uuid.uuid4().hex[:6].upper()
    sala = Sala(
        codigo=codigo,
        anfitrion_id=usuarios[0].id,
        estado=EstadoSalaEnum.EN_CURSO,
        turno_actual=0,
    )
    sesion.add(sala)
    await sesion.flush()

    for orden, usuario in enumerate(usuarios):
        sesion.add(
            SalaJugador(
                sala_id=sala.id, usuario_id=usuario.id, orden_turno=orden, conectado=True
            )
        )
    await sesion.commit()

    sala_cargada = await servicio_salas.obtener_sala_por_codigo(sesion, codigo)
    return sala_cargada, [u.id for u in usuarios]


async def _jugar_ronda(sesion, sala, lector_id, votos, prediccion):
    await servicio_juego.robar_carta(sesion, sala, lector_id)
    await servicio_juego.registrar_prediccion(sesion, sala, lector_id, prediccion)

    ronda = None
    for usuario_id, opcion in votos:
        ronda, _, _ = await servicio_juego.registrar_voto(sesion, sala, usuario_id, opcion)
    return ronda


CASOS_RESOLUCION = [
    pytest.param(3, [1, 1, 1], PrediccionEnum.TODOS_1, "todos_1", True, id="unanimidad_1_acierto"),
    pytest.param(
        3, [1, 1, 1], PrediccionEnum.MAYORIA_1, "todos_1", False, id="unanimidad_1_prediccion_mayoria_no_acierta"
    ),
    pytest.param(3, [1, 1, 2], PrediccionEnum.MAYORIA_1, "mayoria_1", True, id="mayoria_1_acierto"),
    pytest.param(
        3, [1, 1, 2], PrediccionEnum.TODOS_1, "mayoria_1", False, id="mayoria_1_prediccion_todos_no_acierta"
    ),
    pytest.param(3, [2, 2, 2], PrediccionEnum.TODOS_2, "todos_2", True, id="unanimidad_2_acierto"),
    pytest.param(3, [2, 2, 1], PrediccionEnum.MAYORIA_2, "mayoria_2", True, id="mayoria_2_acierto"),
    pytest.param(
        3, [1, 1, 2], PrediccionEnum.MAYORIA_2, "mayoria_1", False, id="mayoria_1_prediccion_mayoria_2_no_acierta"
    ),
    pytest.param(
        2, [1, 2], PrediccionEnum.MAYORIA_1, "empate", False, id="empate_nunca_acierta"
    ),
]


@pytest.mark.parametrize("n_voters,opciones,prediccion,resultado_esperado,acierto_esperado", CASOS_RESOLUCION)
async def test_resolucion_ronda(
    sesion_prueba: AsyncSession,
    n_voters: int,
    opciones: list[int],
    prediccion: PrediccionEnum,
    resultado_esperado: str,
    acierto_esperado: bool,
) -> None:
    sala, usuarios = await _preparar_sala(sesion_prueba, n_voters, "u")
    lector_id, *votantes = usuarios
    votos = list(zip(votantes, opciones))

    ronda = await _jugar_ronda(sesion_prueba, sala, lector_id, votos, prediccion)

    assert ronda.resultado.value == resultado_esperado
    assert ronda.acierto is acierto_esperado

    lector_jugador = await sesion_prueba.scalar(
        select(SalaJugador).where(
            SalaJugador.sala_id == sala.id, SalaJugador.usuario_id == lector_id
        )
    )
    assert lector_jugador.puntos == (1 if acierto_esperado else 0)


async def test_solo_lector_puede_robar_carta(sesion_prueba: AsyncSession) -> None:
    sala, usuarios = await _preparar_sala(sesion_prueba, 2, "r")
    lector_id, *votantes = usuarios

    with pytest.raises(ErrorAplicacion) as info:
        await servicio_juego.robar_carta(sesion_prueba, sala, votantes[0])
    assert info.value.status_code == 403


async def test_lector_no_puede_votar(sesion_prueba: AsyncSession) -> None:
    sala, usuarios = await _preparar_sala(sesion_prueba, 2, "l")
    lector_id, *votantes = usuarios

    await servicio_juego.robar_carta(sesion_prueba, sala, lector_id)
    await servicio_juego.registrar_prediccion(sesion_prueba, sala, lector_id, PrediccionEnum.MAYORIA_1)

    with pytest.raises(ErrorAplicacion) as info:
        await servicio_juego.registrar_voto(sesion_prueba, sala, lector_id, 1)
    assert info.value.status_code == 403


async def test_no_se_puede_votar_dos_veces(sesion_prueba: AsyncSession) -> None:
    sala, usuarios = await _preparar_sala(sesion_prueba, 2, "d")
    lector_id, *votantes = usuarios

    await servicio_juego.robar_carta(sesion_prueba, sala, lector_id)
    await servicio_juego.registrar_prediccion(sesion_prueba, sala, lector_id, PrediccionEnum.MAYORIA_1)
    await servicio_juego.registrar_voto(sesion_prueba, sala, votantes[0], 1)

    with pytest.raises(ErrorAplicacion) as info:
        await servicio_juego.registrar_voto(sesion_prueba, sala, votantes[0], 2)
    assert info.value.status_code == 409


async def test_no_repite_pregunta_ya_usada(sesion_prueba: AsyncSession) -> None:
    sala, usuarios = await _preparar_sala(sesion_prueba, 2, "p")
    lector_id, *votantes = usuarios

    ronda_1 = await servicio_juego.robar_carta(sesion_prueba, sala, lector_id)
    await servicio_juego.registrar_prediccion(sesion_prueba, sala, lector_id, PrediccionEnum.MAYORIA_1)
    await servicio_juego.registrar_voto(sesion_prueba, sala, votantes[0], 1)
    await servicio_juego.registrar_voto(sesion_prueba, sala, votantes[1], 1)

    await servicio_juego.avanzar_turno(sesion_prueba, sala, lector_id)

    with pytest.raises(ErrorAplicacion) as info:
        await servicio_juego.robar_carta(sesion_prueba, sala, votantes[0])
    assert info.value.status_code == 409
    assert "no quedan preguntas" in info.value.detalle.lower()


async def test_avanzar_turno_rota_lector(sesion_prueba: AsyncSession) -> None:
    sala, usuarios = await _preparar_sala(sesion_prueba, 2, "t")
    lector_id, votante_1, votante_2 = usuarios

    await servicio_juego.robar_carta(sesion_prueba, sala, lector_id)
    await servicio_juego.registrar_prediccion(sesion_prueba, sala, lector_id, PrediccionEnum.MAYORIA_1)
    await servicio_juego.registrar_voto(sesion_prueba, sala, votante_1, 1)
    await servicio_juego.registrar_voto(sesion_prueba, sala, votante_2, 1)

    sala_actualizada = await servicio_juego.avanzar_turno(sesion_prueba, sala, lector_id)
    nuevo_lector = servicio_juego.lector_actual(sala_actualizada)
    assert nuevo_lector.usuario_id == votante_1


async def test_no_avanza_turno_con_ronda_sin_resolver(sesion_prueba: AsyncSession) -> None:
    sala, usuarios = await _preparar_sala(sesion_prueba, 2, "s")
    lector_id, *votantes = usuarios

    await servicio_juego.robar_carta(sesion_prueba, sala, lector_id)

    with pytest.raises(ErrorAplicacion) as info:
        await servicio_juego.avanzar_turno(sesion_prueba, sala, lector_id)
    assert info.value.status_code == 409


async def test_anfitrion_fuerza_turno_si_lector_desconectado(sesion_prueba: AsyncSession) -> None:
    sala, usuarios = await _preparar_sala(sesion_prueba, 2, "desc")
    anfitrion_id = usuarios[0]
    # anfitrion_id tiene orden_turno 0; forzamos turno_actual=1 para que el lector actual
    # (orden_turno == turno_actual) sea un jugador distinto del anfitrión.
    sala.turno_actual = 1
    await sesion_prueba.commit()
    sala = await servicio_salas.obtener_sala_por_codigo(sesion_prueba, sala.codigo)

    lector = servicio_juego.lector_actual(sala)
    await servicio_juego.robar_carta(sesion_prueba, sala, lector.usuario_id)

    lector.conectado = False
    await sesion_prueba.commit()
    sala = await servicio_salas.obtener_sala_por_codigo(sesion_prueba, sala.codigo)

    # El anfitrión puede forzar el avance aunque la ronda quedó sin resolver,
    # porque el lector actual está desconectado (decisión #7).
    sala_actualizada = await servicio_juego.avanzar_turno(sesion_prueba, sala, anfitrion_id)
    assert sala_actualizada.turno_actual == 2
