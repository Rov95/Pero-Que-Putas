import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import EstadoRondaEnum, EstadoSalaEnum, PrediccionEnum, ResultadoEnum
from app.errores import ErrorAplicacion
from app.models.pregunta import Pregunta
from app.models.ronda import Ronda, Voto
from app.models.sala import Sala, SalaJugador


def lector_actual(sala: Sala) -> SalaJugador:
    n = len(sala.jugadores)
    turno = sala.turno_actual % n
    for jugador in sala.jugadores:
        if jugador.orden_turno == turno:
            return jugador
    raise ErrorAplicacion("No se pudo determinar el lector actual", status_code=500)


async def obtener_ronda_activa(sesion: AsyncSession, sala_id: uuid.UUID) -> Ronda | None:
    return await sesion.scalar(
        select(Ronda)
        .options(selectinload(Ronda.pregunta).selectinload(Pregunta.opciones))
        .where(Ronda.sala_id == sala_id)
        .order_by(Ronda.numero.desc())
        .limit(1)
        .execution_options(populate_existing=True)
    )


async def robar_carta(sesion: AsyncSession, sala: Sala, usuario_id: uuid.UUID) -> Ronda:
    if sala.estado != EstadoSalaEnum.EN_CURSO:
        raise ErrorAplicacion("La partida no está en curso", status_code=409)

    ronda_activa = await obtener_ronda_activa(sesion, sala.id)
    if ronda_activa is not None and ronda_activa.estado != EstadoRondaEnum.RESUELTA:
        raise ErrorAplicacion("Ya hay una ronda en curso", status_code=409)

    lector = lector_actual(sala)
    if lector.usuario_id != usuario_id:
        raise ErrorAplicacion("Solo el lector puede robar una carta", status_code=403)

    usadas = select(Ronda.pregunta_id).where(Ronda.sala_id == sala.id)
    pregunta = await sesion.scalar(
        select(Pregunta)
        .options(selectinload(Pregunta.opciones))
        .where(Pregunta.eliminada.is_(False), Pregunta.id.notin_(usadas))
        .order_by(func.random())
        .limit(1)
    )
    if pregunta is None:
        raise ErrorAplicacion("No quedan preguntas disponibles", status_code=409)

    numero_anterior = await sesion.scalar(
        select(func.count()).select_from(Ronda).where(Ronda.sala_id == sala.id)
    )

    ronda = Ronda(
        sala_id=sala.id,
        numero=(numero_anterior or 0) + 1,
        pregunta_id=pregunta.id,
        lector_id=usuario_id,
        estado=EstadoRondaEnum.LEYENDO,
    )
    sesion.add(ronda)
    await sesion.commit()

    ronda.pregunta = pregunta
    return ronda


async def registrar_prediccion(
    sesion: AsyncSession, sala: Sala, usuario_id: uuid.UUID, prediccion: PrediccionEnum
) -> Ronda:
    ronda = await obtener_ronda_activa(sesion, sala.id)
    if ronda is None or ronda.estado != EstadoRondaEnum.LEYENDO:
        raise ErrorAplicacion("No hay una ronda esperando predicción", status_code=409)
    if ronda.lector_id != usuario_id:
        raise ErrorAplicacion("Solo el lector puede predecir", status_code=403)

    ronda.prediccion = prediccion
    ronda.estado = EstadoRondaEnum.VOTANDO
    await sesion.commit()
    return ronda


async def registrar_voto(
    sesion: AsyncSession, sala: Sala, usuario_id: uuid.UUID, opcion: int
) -> tuple[Ronda, int, int]:
    ronda = await obtener_ronda_activa(sesion, sala.id)
    if ronda is None or ronda.estado != EstadoRondaEnum.VOTANDO:
        raise ErrorAplicacion("No hay una ronda esperando votos", status_code=409)
    if ronda.lector_id == usuario_id:
        raise ErrorAplicacion("El lector no vota", status_code=403)

    ya_voto = await sesion.scalar(
        select(Voto).where(Voto.ronda_id == ronda.id, Voto.usuario_id == usuario_id)
    )
    if ya_voto is not None:
        raise ErrorAplicacion("Ya votaste en esta ronda", status_code=409)

    sesion.add(Voto(ronda_id=ronda.id, usuario_id=usuario_id, opcion=opcion))
    await sesion.commit()

    votos_recibidos = await sesion.scalar(
        select(func.count()).select_from(Voto).where(Voto.ronda_id == ronda.id)
    )
    votos_esperados = sum(
        1
        for jugador in sala.jugadores
        if jugador.usuario_id != ronda.lector_id and jugador.conectado
    )

    if votos_recibidos >= votos_esperados:
        await _resolver_ronda(sesion, sala, ronda)

    return ronda, votos_recibidos, votos_esperados


async def _resolver_ronda(sesion: AsyncSession, sala: Sala, ronda: Ronda) -> None:
    votos = list(
        (await sesion.scalars(select(Voto).where(Voto.ronda_id == ronda.id))).all()
    )
    votos_1 = sum(1 for v in votos if v.opcion == 1)
    votos_2 = sum(1 for v in votos if v.opcion == 2)
    total = votos_1 + votos_2

    if total == 0:
        resultado = ResultadoEnum.EMPATE
    elif votos_1 == total:
        resultado = ResultadoEnum.TODOS_1
    elif votos_2 == total:
        resultado = ResultadoEnum.TODOS_2
    elif votos_1 > votos_2:
        resultado = ResultadoEnum.MAYORIA_1
    elif votos_2 > votos_1:
        resultado = ResultadoEnum.MAYORIA_2
    else:
        resultado = ResultadoEnum.EMPATE

    acierto = ronda.prediccion is not None and ronda.prediccion.value == resultado.value

    # Guarda de idempotencia: dos votos casi simultáneos (cada uno en su propia sesión
    # de WS) pueden cruzar el umbral de votos_esperados a la vez y llegar aquí los dos.
    # Esta actualización atómica solo afecta la fila si todavía sigue "votando"; bajo
    # READ COMMITTED, si dos UPDATE concurrentes chocan, Postgres serializa la segunda
    # contra el estado ya confirmado por la primera, así que como mucho una gana.
    # synchronize_session=False: por defecto SQLAlchemy "sincroniza" evaluando el WHERE
    # contra el objeto ya cargado en memoria (no contra lo que realmente cambió en la
    # fila), así que sin esto el objeto local se marca RESUELTA aunque el UPDATE real
    # haya afectado 0 filas — justo el caso que esta guarda necesita distinguir.
    resultado_update = await sesion.execute(
        update(Ronda)
        .where(Ronda.id == ronda.id, Ronda.estado == EstadoRondaEnum.VOTANDO)
        .values(resultado=resultado, acierto=acierto, estado=EstadoRondaEnum.RESUELTA)
        .execution_options(synchronize_session=False)
    )
    if resultado_update.rowcount == 0:
        # Otra sesión ya resolvió esta ronda: no-op, para no duplicar el
        # resultado_ronda ni puntuar dos veces al lector.
        return

    ronda.resultado = resultado
    ronda.acierto = acierto
    ronda.estado = EstadoRondaEnum.RESUELTA

    if acierto:
        lector_jugador = next(j for j in sala.jugadores if j.usuario_id == ronda.lector_id)
        lector_jugador.puntos += 1

    await sesion.commit()


async def avanzar_turno(sesion: AsyncSession, sala: Sala, usuario_id: uuid.UUID) -> Sala:
    lector = lector_actual(sala)
    if usuario_id not in (lector.usuario_id, sala.anfitrion_id):
        raise ErrorAplicacion(
            "Solo el lector o el anfitrión pueden avanzar el turno", status_code=403
        )

    ronda_activa = await obtener_ronda_activa(sesion, sala.id)
    ronda_sin_resolver = ronda_activa is not None and ronda_activa.estado != EstadoRondaEnum.RESUELTA
    if ronda_sin_resolver and lector.conectado:
        raise ErrorAplicacion("Termina la ronda actual antes de continuar", status_code=409)

    sala.turno_actual += 1
    await sesion.commit()
    return sala
