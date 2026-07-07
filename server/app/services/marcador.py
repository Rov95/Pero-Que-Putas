import uuid

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marcador import MarcadorHistorico
from app.models.usuario import Usuario


async def obtener_marcador(sesion: AsyncSession, usuario_id: uuid.UUID | None) -> list[dict]:
    consulta = (
        select(
            Usuario.id.label("usuario_id"),
            Usuario.username,
            func.sum(MarcadorHistorico.puntos_finales).label("puntos_totales"),
            func.count(MarcadorHistorico.id).label("partidas"),
            func.sum(case((MarcadorHistorico.gano.is_(True), 1), else_=0)).label("victorias"),
        )
        .join(MarcadorHistorico, MarcadorHistorico.usuario_id == Usuario.id)
        .group_by(Usuario.id, Usuario.username)
        .order_by(func.sum(MarcadorHistorico.puntos_finales).desc())
    )
    if usuario_id is not None:
        consulta = consulta.where(Usuario.id == usuario_id)

    filas = (await sesion.execute(consulta)).all()
    return [
        {
            "username": fila.username,
            "puntos_totales": fila.puntos_totales,
            "partidas": fila.partidas,
            "victorias": fila.victorias,
        }
        for fila in filas
    ]
