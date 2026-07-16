import asyncio

from fastapi import FastAPI

from app.bots.jugador import BotJugador
from app.models.usuario import Usuario

# Tope defensivo para la parada cooperativa (§ BotJugador._jugar). Si un bot no
# reacciona a `detener()` en este plazo (no debería pasar: el loop sondea cada
# INTERVALO_SONDEO_SEGUNDOS), se recurre a cancelar la tarea como último recurso.
ESPERA_PARADA_SEGUNDOS = 5.0


class RegistroBots:
    def __init__(self) -> None:
        self._entradas: dict[str, list[tuple[asyncio.Task[None], BotJugador]]] = {}

    def iniciar_bots(self, app: FastAPI, codigo: str, bots: list[Usuario]) -> None:
        entradas = self._entradas.setdefault(codigo, [])
        for bot in bots:
            jugador = BotJugador(app, codigo, bot.id, bot.username)
            tarea = asyncio.create_task(jugador.correr(), name=f"bot-{codigo}-{bot.id}")
            entradas.append((tarea, jugador))
            tarea.add_done_callback(lambda tarea, codigo=codigo: self._podar(codigo, tarea))

    def _podar(self, codigo: str, tarea: "asyncio.Task[None]") -> None:
        entradas = self._entradas.get(codigo)
        if entradas is None:
            return
        restantes = [e for e in entradas if e[0] is not tarea]
        if restantes:
            self._entradas[codigo] = restantes
        else:
            self._entradas.pop(codigo, None)

    async def detener_bots(self, codigo: str) -> None:
        entradas = self._entradas.pop(codigo, None)
        if not entradas:
            return
        tareas = [tarea for tarea, _ in entradas]
        for _, jugador in entradas:
            jugador.detener()
        try:
            await asyncio.wait_for(
                asyncio.gather(*tareas, return_exceptions=True), timeout=ESPERA_PARADA_SEGUNDOS
            )
        except TimeoutError:
            for tarea in tareas:
                tarea.cancel()
            await asyncio.gather(*tareas, return_exceptions=True)

    async def detener_todos(self) -> None:
        for codigo in list(self._entradas.keys()):
            await self.detener_bots(codigo)

    def cantidad_activos(self, codigo: str | None = None) -> int:
        if codigo is not None:
            return len(self._entradas.get(codigo, ()))
        return sum(len(entradas) for entradas in self._entradas.values())


registro = RegistroBots()
