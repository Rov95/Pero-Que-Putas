import uuid
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import EstadoRondaEnum
from app.database import obtener_sesion
from app.errores import ErrorAplicacion
from app.models.ronda import Voto
from app.models.sala import Sala, SalaJugador
from app.schemas.juego import PrediccionSecretaDatos, VotoDatos
from app.services import juego as servicio_juego
from app.services import salas as servicio_salas
from app.services import sesiones as servicio_sesiones
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


def _jugador_payload(jugador: SalaJugador) -> dict[str, Any]:
    return {"usuario_id": str(jugador.usuario_id), "username": jugador.usuario.username}


def _pregunta_payload(pregunta) -> dict[str, Any]:
    por_numero = {opcion.numero: opcion.texto for opcion in pregunta.opciones}
    return {
        "id": str(pregunta.id),
        "enunciado": pregunta.enunciado,
        "opcion_1": por_numero[1],
        "opcion_2": por_numero[2],
    }


async def _despachar(
    sesion: AsyncSession, codigo: str, usuario_id: uuid.UUID, evento: str, datos: dict[str, Any]
) -> None:
    sala = await servicio_salas.obtener_sala_por_codigo(sesion, codigo)

    if evento == "robar_carta":
        ronda = await servicio_juego.robar_carta(sesion, sala, usuario_id)
        await manager.difundir(
            codigo, eventos.carta_robada(ronda.id, _pregunta_payload(ronda.pregunta))
        )
        return

    if evento == "prediccion_secreta":
        try:
            payload = PrediccionSecretaDatos.model_validate(datos)
        except ValidationError as exc:
            raise ErrorAplicacion("Predicción inválida", status_code=400) from exc
        await servicio_juego.registrar_prediccion(sesion, sala, usuario_id, payload.prediccion)
        await manager.difundir(codigo, eventos.prediccion_registrada(usuario_id))
        return

    if evento == "voto":
        try:
            payload = VotoDatos.model_validate(datos)
        except ValidationError as exc:
            raise ErrorAplicacion("Voto inválido", status_code=400) from exc
        ronda, votos_recibidos, votos_esperados = await servicio_juego.registrar_voto(
            sesion, sala, usuario_id, payload.opcion
        )
        await manager.difundir(codigo, eventos.voto_registrado(votos_recibidos, votos_esperados))
        if ronda.estado == EstadoRondaEnum.RESUELTA:
            sala_actualizada = await servicio_salas.obtener_sala_por_codigo(sesion, codigo)
            jugadores_por_id = {j.usuario_id: j for j in sala_actualizada.jugadores}
            votos = await sesion.scalars(select(Voto).where(Voto.ronda_id == ronda.id))
            votos_payload = [
                {
                    "usuario_id": str(v.usuario_id),
                    "username": jugadores_por_id[v.usuario_id].usuario.username,
                    "opcion": v.opcion,
                }
                for v in votos.all()
            ]
            puntos_lector = jugadores_por_id[ronda.lector_id].puntos
            await manager.difundir(
                codigo,
                eventos.resultado_ronda(
                    votos_payload,
                    ronda.resultado.value,
                    ronda.prediccion.value,
                    ronda.acierto,
                    puntos_lector,
                ),
            )
        return

    if evento == "siguiente_turno":
        sala_actualizada = await servicio_juego.avanzar_turno(sesion, sala, usuario_id)
        nuevo_lector = servicio_juego.lector_actual(sala_actualizada)
        await manager.difundir(
            codigo,
            eventos.turno_actual(sala_actualizada.turno_actual, _jugador_payload(nuevo_lector)),
        )
        return

    raise ErrorAplicacion(f"Evento desconocido: {evento}", status_code=400)


@router.websocket("/ws/salas/{codigo}")
async def endpoint_sala(
    websocket: WebSocket,
    codigo: str,
    token: str = "",
    sesion: AsyncSession = Depends(obtener_sesion),
) -> None:
    await websocket.accept()

    try:
        usuario, _ = await servicio_sesiones.usuario_por_token(sesion, token)
    except ErrorAplicacion:
        await websocket.close(code=4001, reason="Sesión inválida")
        return
    usuario_id = usuario.id

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
            mensaje = await websocket.receive_json()
            evento = mensaje.get("evento")
            datos = mensaje.get("datos") or {}
            try:
                await _despachar(sesion, codigo, usuario_id, evento, datos)
            except ErrorAplicacion as exc:
                await manager.enviar_a(codigo, usuario_id, eventos.error(exc.detalle))
    except WebSocketDisconnect:
        pass
    finally:
        manager.desconectar(codigo, usuario_id)
        jugador.conectado = False
        await sesion.commit()
        await manager.difundir(codigo, eventos.jugador_salio(usuario_id, username))
