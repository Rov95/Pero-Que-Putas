import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.constants import EstadoSalaEnum
from app.models.marcador import MarcadorHistorico
from app.models.sala import Sala, SalaJugador
from app.models.usuario import Usuario
from app.services import salas as servicio_salas


async def _preparar_sala_con_puntos(sesion: AsyncSession) -> tuple[str, uuid.UUID]:
    usuarios = [Usuario(username=f"atomico{i}") for i in range(2)]
    sesion.add_all(usuarios)
    await sesion.flush()

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
                sala_id=sala.id,
                usuario_id=usuario.id,
                orden_turno=orden,
                puntos=5,
                conectado=True,
            )
        )
    await sesion.commit()
    return codigo, usuarios[0].id


async def test_finalizar_es_todo_o_nada(
    sesion_prueba: AsyncSession, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    codigo, anfitrion_id = await _preparar_sala_con_puntos(sesion_prueba)

    async def commit_falla() -> None:
        raise RuntimeError("fallo simulado durante el commit")

    monkeypatch.setattr(sesion_prueba, "commit", commit_falla)

    with pytest.raises(RuntimeError):
        await servicio_salas.finalizar_partida(sesion_prueba, codigo, anfitrion_id)

    monkeypatch.undo()

    verificacion_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with verificacion_factory() as verificacion:
        marcador_rows = (
            await verificacion.scalars(select(MarcadorHistorico))
        ).all()
        assert marcador_rows == []

        sala = await verificacion.scalar(select(Sala).where(Sala.codigo == codigo))
        assert sala.estado == EstadoSalaEnum.EN_CURSO

        jugadores = (
            await verificacion.scalars(
                select(SalaJugador).where(SalaJugador.sala_id == sala.id)
            )
        ).all()
        assert all(j.puntos == 5 for j in jugadores)
