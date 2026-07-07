import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import EstadoSalaEnum
from app.errores import ErrorAplicacion
from app.models.sala import Sala, SalaJugador
from app.models.usuario import Usuario

ALFABETO_CODIGO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # sin 0/O, 1/I/L
LONGITUD_CODIGO = 6
INTENTOS_CODIGO = 10


def _generar_codigo() -> str:
    return "".join(random.choices(ALFABETO_CODIGO, k=LONGITUD_CODIGO))


async def _obtener_usuario_o_404(sesion: AsyncSession, usuario_id: uuid.UUID) -> Usuario:
    usuario = await sesion.get(Usuario, usuario_id)
    if usuario is None:
        raise ErrorAplicacion("Usuario no encontrado", status_code=404)
    return usuario


async def obtener_sala_por_codigo(sesion: AsyncSession, codigo: str) -> Sala:
    sala = await sesion.scalar(
        select(Sala)
        .options(selectinload(Sala.jugadores).selectinload(SalaJugador.usuario))
        .where(Sala.codigo == codigo)
        .execution_options(populate_existing=True)
    )
    if sala is None:
        raise ErrorAplicacion("Sala no encontrada", status_code=404)
    return sala


async def crear_sala(sesion: AsyncSession, usuario_id: uuid.UUID) -> Sala:
    await _obtener_usuario_o_404(sesion, usuario_id)

    for _ in range(INTENTOS_CODIGO):
        codigo = _generar_codigo()
        existe = await sesion.scalar(select(Sala.id).where(Sala.codigo == codigo))
        if existe is None:
            break
    else:
        raise ErrorAplicacion("No se pudo generar un código de sala único", status_code=500)

    sala = Sala(codigo=codigo, anfitrion_id=usuario_id)
    sesion.add(sala)
    await sesion.flush()

    sesion.add(SalaJugador(sala_id=sala.id, usuario_id=usuario_id))
    await sesion.commit()

    return await obtener_sala_por_codigo(sesion, codigo)


async def unirse_a_sala(sesion: AsyncSession, codigo: str, usuario_id: uuid.UUID) -> Sala:
    sala = await obtener_sala_por_codigo(sesion, codigo)
    if sala.estado != EstadoSalaEnum.ESPERANDO:
        raise ErrorAplicacion("La partida ya empezó", status_code=409)

    await _obtener_usuario_o_404(sesion, usuario_id)

    ya_unido = any(jugador.usuario_id == usuario_id for jugador in sala.jugadores)
    if not ya_unido:
        sesion.add(SalaJugador(sala_id=sala.id, usuario_id=usuario_id))
        await sesion.commit()

    return await obtener_sala_por_codigo(sesion, codigo)


async def iniciar_partida(sesion: AsyncSession, codigo: str, usuario_id: uuid.UUID) -> Sala:
    sala = await obtener_sala_por_codigo(sesion, codigo)
    if sala.anfitrion_id != usuario_id:
        raise ErrorAplicacion("Solo el anfitrión puede iniciar la partida", status_code=403)
    if sala.estado != EstadoSalaEnum.ESPERANDO:
        raise ErrorAplicacion("La partida ya empezó", status_code=409)

    jugadores = list(sala.jugadores)
    random.shuffle(jugadores)
    for orden, jugador in enumerate(jugadores):
        jugador.orden_turno = orden

    sala.estado = EstadoSalaEnum.EN_CURSO
    sala.turno_actual = 0
    await sesion.commit()

    return await obtener_sala_por_codigo(sesion, codigo)
