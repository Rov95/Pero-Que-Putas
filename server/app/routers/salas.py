from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import obtener_sesion
from app.models.sala import Sala
from app.schemas.sala import IniciarSala, JugadorLeer, SalaCrear, SalaLeer, UnirseSala
from app.services import juego as servicio_juego
from app.services import salas as servicio_salas
from app.websocket import eventos
from app.websocket.manager import manager

router = APIRouter(prefix="/api/salas", tags=["salas"])


def _a_sala_leer(sala: Sala) -> SalaLeer:
    return SalaLeer(
        id=sala.id,
        codigo=sala.codigo,
        estado=sala.estado,
        anfitrion_id=sala.anfitrion_id,
        turno_actual=sala.turno_actual,
        creado_en=sala.creado_en,
        jugadores=[
            JugadorLeer(
                usuario_id=jugador.usuario_id,
                username=jugador.usuario.username,
                orden_turno=jugador.orden_turno,
                puntos=jugador.puntos,
                conectado=jugador.conectado,
            )
            for jugador in sala.jugadores
        ],
    )


def _jugador_payload(jugador) -> dict:
    return {"usuario_id": str(jugador.usuario_id), "username": jugador.usuario.username}


@router.post("", response_model=SalaLeer, status_code=status.HTTP_201_CREATED)
async def crear_sala(
    datos: SalaCrear, sesion: AsyncSession = Depends(obtener_sesion)
) -> SalaLeer:
    sala = await servicio_salas.crear_sala(sesion, datos.usuario_id)
    return _a_sala_leer(sala)


@router.post("/{codigo}/unirse", response_model=SalaLeer)
async def unirse_a_sala(
    codigo: str, datos: UnirseSala, sesion: AsyncSession = Depends(obtener_sesion)
) -> SalaLeer:
    sala = await servicio_salas.unirse_a_sala(sesion, codigo, datos.usuario_id)
    return _a_sala_leer(sala)


@router.get("/{codigo}", response_model=SalaLeer)
async def consultar_sala(codigo: str, sesion: AsyncSession = Depends(obtener_sesion)) -> SalaLeer:
    sala = await servicio_salas.obtener_sala_por_codigo(sesion, codigo)
    return _a_sala_leer(sala)


@router.post("/{codigo}/iniciar", response_model=SalaLeer)
async def iniciar_partida(
    codigo: str, datos: IniciarSala, sesion: AsyncSession = Depends(obtener_sesion)
) -> SalaLeer:
    sala = await servicio_salas.iniciar_partida(sesion, codigo, datos.usuario_id)

    orden = sorted(
        (_jugador_payload(j) | {"orden_turno": j.orden_turno} for j in sala.jugadores),
        key=lambda j: j["orden_turno"],
    )
    lector = servicio_juego.lector_actual(sala)
    lector_payload = _jugador_payload(lector)
    await manager.difundir(codigo, eventos.partida_iniciada(orden, lector_payload))
    await manager.difundir(codigo, eventos.turno_actual(sala.turno_actual, lector_payload))

    return _a_sala_leer(sala)
