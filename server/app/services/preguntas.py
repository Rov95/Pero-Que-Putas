import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errores import ErrorAplicacion
from app.models.pregunta import Opcion, Pregunta
from app.models.ronda import Ronda


async def crear_pregunta(
    sesion: AsyncSession, enunciado: str, opcion_1: str, opcion_2: str
) -> Pregunta:
    pregunta = Pregunta(enunciado=enunciado)
    pregunta.opciones = [
        Opcion(numero=1, texto=opcion_1),
        Opcion(numero=2, texto=opcion_2),
    ]
    sesion.add(pregunta)
    await sesion.commit()
    await sesion.refresh(pregunta, attribute_names=["opciones"])
    return pregunta


async def listar_preguntas(sesion: AsyncSession, desplazamiento: int, limite: int) -> list[Pregunta]:
    resultado = await sesion.scalars(
        select(Pregunta)
        .options(selectinload(Pregunta.opciones))
        .where(Pregunta.eliminada.is_(False))
        .order_by(Pregunta.creado_en)
        .offset(desplazamiento)
        .limit(limite)
    )
    return list(resultado.all())


async def obtener_pregunta(sesion: AsyncSession, pregunta_id: uuid.UUID) -> Pregunta:
    pregunta = await sesion.scalar(
        select(Pregunta)
        .options(selectinload(Pregunta.opciones))
        .where(Pregunta.id == pregunta_id, Pregunta.eliminada.is_(False))
    )
    if pregunta is None:
        raise ErrorAplicacion("Pregunta no encontrada", status_code=404)
    return pregunta


async def obtener_opciones(sesion: AsyncSession, pregunta_id: uuid.UUID) -> Pregunta:
    return await obtener_pregunta(sesion, pregunta_id)


async def actualizar_pregunta(
    sesion: AsyncSession, pregunta_id: uuid.UUID, enunciado: str, opcion_1: str, opcion_2: str
) -> Pregunta:
    pregunta = await obtener_pregunta(sesion, pregunta_id)
    pregunta.enunciado = enunciado
    for opcion in pregunta.opciones:
        opcion.texto = opcion_1 if opcion.numero == 1 else opcion_2
    await sesion.commit()
    await sesion.refresh(pregunta, attribute_names=["opciones"])
    return pregunta


async def establecer_opciones(
    sesion: AsyncSession, pregunta_id: uuid.UUID, opcion_1: str, opcion_2: str
) -> Pregunta:
    pregunta = await obtener_pregunta(sesion, pregunta_id)
    for opcion in pregunta.opciones:
        opcion.texto = opcion_1 if opcion.numero == 1 else opcion_2
    await sesion.commit()
    await sesion.refresh(pregunta, attribute_names=["opciones"])
    return pregunta


async def eliminar_pregunta(sesion: AsyncSession, pregunta_id: uuid.UUID) -> None:
    pregunta = await obtener_pregunta(sesion, pregunta_id)
    # rondas.pregunta_id no tiene ON DELETE: una pregunta ya jugada no puede
    # borrarse físicamente sin romper el historial (o una ronda activa), así que
    # se marca eliminada; para el cliente el efecto es el mismo (desaparece del
    # listado y del mazo). Si nunca se jugó, se borra de verdad.
    usada = await sesion.scalar(
        select(Ronda.id).where(Ronda.pregunta_id == pregunta_id).limit(1)
    )
    if usada is None:
        await sesion.delete(pregunta)
    else:
        pregunta.eliminada = True
    await sesion.commit()
