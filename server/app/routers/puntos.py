import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import obtener_sesion
from app.schemas.puntos import MarcadorHistoricoEntrada, PuntoEstablecer, PuntoJugador
from app.services import marcador as servicio_marcador
from app.services import salas as servicio_salas

router = APIRouter(tags=["puntos"])


def _puntos_de_sala(sala) -> list[PuntoJugador]:
    return [
        PuntoJugador(usuario_id=j.usuario_id, username=j.usuario.username, puntos=j.puntos)
        for j in sala.jugadores
    ]


@router.get("/api/salas/{codigo}/puntos", response_model=list[PuntoJugador])
async def obtener_puntos(
    codigo: str, sesion: AsyncSession = Depends(obtener_sesion)
) -> list[PuntoJugador]:
    sala = await servicio_salas.obtener_sala_por_codigo(sesion, codigo)
    return _puntos_de_sala(sala)


@router.put("/api/salas/{codigo}/puntos/{usuario_id}", response_model=PuntoJugador)
async def establecer_puntos(
    codigo: str,
    usuario_id: uuid.UUID,
    datos: PuntoEstablecer,
    sesion: AsyncSession = Depends(obtener_sesion),
) -> PuntoJugador:
    sala = await servicio_salas.establecer_puntos(sesion, codigo, usuario_id, datos.puntos)
    jugador = next(j for j in sala.jugadores if j.usuario_id == usuario_id)
    return PuntoJugador(usuario_id=jugador.usuario_id, username=jugador.usuario.username, puntos=jugador.puntos)


@router.delete("/api/salas/{codigo}/puntos", status_code=status.HTTP_204_NO_CONTENT)
async def reiniciar_puntos(codigo: str, sesion: AsyncSession = Depends(obtener_sesion)) -> None:
    await servicio_salas.reiniciar_puntos(sesion, codigo)


@router.get("/api/marcador", response_model=list[MarcadorHistoricoEntrada])
async def obtener_marcador(
    usuario_id: uuid.UUID | None = Query(None),
    sesion: AsyncSession = Depends(obtener_sesion),
) -> list[MarcadorHistoricoEntrada]:
    filas = await servicio_marcador.obtener_marcador(sesion, usuario_id)
    return [MarcadorHistoricoEntrada(**fila) for fila in filas]
