import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errores import ErrorAplicacion
from app.models.usuario import Usuario

APODOS_BOT = [
    "Luna",
    "Mateo",
    "Sofia",
    "Andres",
    "Camila",
    "Diego",
    "Valentina",
    "Julian",
    "Isabella",
    "Santiago",
]
ALFABETO_SUFIJO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # sin 0/O, 1/I/L
LONGITUD_SUFIJO = 4
INTENTOS_NOMBRE = 10


def _generar_username_bot() -> str:
    apodo = random.choice(APODOS_BOT)
    sufijo = "".join(random.choices(ALFABETO_SUFIJO, k=LONGITUD_SUFIJO))
    return f"Bot-{apodo}-{sufijo}"


async def _crear_usuario_bot(sesion: AsyncSession) -> Usuario:
    for _ in range(INTENTOS_NOMBRE):
        username = _generar_username_bot()
        existe = await sesion.scalar(
            select(Usuario.id).where(func.lower(Usuario.username) == username.lower())
        )
        if existe is None:
            break
    else:
        raise ErrorAplicacion("No se pudo generar un nombre de bot único", status_code=500)

    usuario = Usuario(username=username)
    sesion.add(usuario)
    await sesion.flush()
    return usuario


async def crear_usuarios_bot(sesion: AsyncSession, cantidad: int) -> list[Usuario]:
    return [await _crear_usuario_bot(sesion) for _ in range(cantidad)]
