import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import obtener_sesion
from app.models.sala import Sala, SalaJugador
from app.websocket import eventos
from app.websocket.manager import manager

router = APIRouter()


async def _obtener_jugador(
    sesion: AsyncSession, codigo: str, usuario_id: uuid.UUID
) -> tuple[Sala | None, SalaJugador | None]:
    sala = await sesion.scalar(select(Sala).where(Sala.codigo == codigo))
    if sala is None:
        return None, None

    jugador = await sesion.scalar(
        select(SalaJugador)
        .options(selectinload(SalaJugador.usuario))
        .where(SalaJugador.sala_id == sala.id, SalaJugador.usuario_id == usuario_id)
    )
    return sala, jugador


@router.websocket("/ws/salas/{codigo}")
async def endpoint_sala(
    websocket: WebSocket,
    codigo: str,
    usuario_id: uuid.UUID,
    sesion: AsyncSession = Depends(obtener_sesion),
) -> None:
    await websocket.accept()

    sala, jugador = await _obtener_jugador(sesion, codigo, usuario_id)
    if sala is None:
        await websocket.close(code=4003, reason="Sala no encontrada")
        return
    if jugador is None:
        await websocket.close(code=4003, reason="No perteneces a esta sala")
        return

    username = jugador.usuario.username

    await manager.conectar(codigo, usuario_id, websocket)
    jugador.conectado = True
    await sesion.commit()

    await manager.difundir(codigo, eventos.jugador_unido(usuario_id, username), excluir=usuario_id)

    try:
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        pass
    finally:
        manager.desconectar(codigo, usuario_id)
        jugador.conectado = False
        await sesion.commit()
        await manager.difundir(codigo, eventos.jugador_salio(usuario_id, username))
