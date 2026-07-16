import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import obtener_sesion
from app.models.pregunta import Pregunta
from app.schemas.pregunta import OpcionesCrear, OpcionesLeer, PreguntaCrear, PreguntaLeer
from app.services import preguntas as servicio_preguntas

router = APIRouter(prefix="/api/preguntas", tags=["preguntas"])


def _a_opciones_leer(pregunta: Pregunta) -> OpcionesLeer:
    por_numero = {opcion.numero: opcion.texto for opcion in pregunta.opciones}
    return OpcionesLeer(opcion_1=por_numero[1], opcion_2=por_numero[2])


@router.get("", response_model=list[PreguntaLeer])
async def listar_preguntas(
    desplazamiento: int = Query(0, ge=0),
    limite: int = Query(20, ge=1, le=100),
    sesion: AsyncSession = Depends(obtener_sesion),
) -> list[PreguntaLeer]:
    preguntas = await servicio_preguntas.listar_preguntas(sesion, desplazamiento, limite)
    return [PreguntaLeer.model_validate(p) for p in preguntas]


@router.post("", response_model=PreguntaLeer, status_code=status.HTTP_201_CREATED)
async def crear_pregunta(
    datos: PreguntaCrear, sesion: AsyncSession = Depends(obtener_sesion)
) -> PreguntaLeer:
    pregunta = await servicio_preguntas.crear_pregunta(
        sesion, datos.enunciado, datos.opcion_1, datos.opcion_2
    )
    return PreguntaLeer.model_validate(pregunta)


@router.get("/{pregunta_id}", response_model=PreguntaLeer)
async def obtener_pregunta(
    pregunta_id: uuid.UUID, sesion: AsyncSession = Depends(obtener_sesion)
) -> PreguntaLeer:
    pregunta = await servicio_preguntas.obtener_pregunta(sesion, pregunta_id)
    return PreguntaLeer.model_validate(pregunta)


@router.put("/{pregunta_id}", response_model=PreguntaLeer)
async def actualizar_pregunta(
    pregunta_id: uuid.UUID,
    datos: PreguntaCrear,
    sesion: AsyncSession = Depends(obtener_sesion),
) -> PreguntaLeer:
    pregunta = await servicio_preguntas.actualizar_pregunta(
        sesion, pregunta_id, datos.enunciado, datos.opcion_1, datos.opcion_2
    )
    return PreguntaLeer.model_validate(pregunta)


@router.get("/{pregunta_id}/opciones", response_model=OpcionesLeer)
async def obtener_opciones(
    pregunta_id: uuid.UUID, sesion: AsyncSession = Depends(obtener_sesion)
) -> OpcionesLeer:
    pregunta = await servicio_preguntas.obtener_opciones(sesion, pregunta_id)
    return _a_opciones_leer(pregunta)


@router.put("/{pregunta_id}/opciones", response_model=OpcionesLeer)
async def establecer_opciones(
    pregunta_id: uuid.UUID,
    datos: OpcionesCrear,
    sesion: AsyncSession = Depends(obtener_sesion),
) -> OpcionesLeer:
    pregunta = await servicio_preguntas.establecer_opciones(
        sesion, pregunta_id, datos.opcion_1, datos.opcion_2
    )
    return _a_opciones_leer(pregunta)


@router.delete("/{pregunta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_pregunta(
    pregunta_id: uuid.UUID, sesion: AsyncSession = Depends(obtener_sesion)
) -> None:
    await servicio_preguntas.eliminar_pregunta(sesion, pregunta_id)
