#!/usr/bin/env python
"""Postgres local para Pero Qué Putas, sin Docker.

Envuelve `pgserver` (un binario de Postgres autocontenido, sin root, que el
backend ya usa en sus tests) para levantar una base de datos de desarrollo
cuando no hay Docker ni un Postgres del sistema instalado.

Se ejecuta con el entorno del backend (que es quien tiene `pgserver`):

    uv run --project server python scripts/db.py start    # arranca e imprime la DATABASE_URL
    uv run --project server python scripts/db.py url       # imprime la DATABASE_URL (sin ruido)
    uv run --project server python scripts/db.py stop       # detiene la instancia
    uv run --project server python scripts/db.py status     # ¿está corriendo?

Los datos viven en `<repo>/.local/pgdata` (ignorado por git). La instancia es un
demonio real (`pg_ctl`), así que sigue viva aunque este script termine; usa un
socket Unix, por eso la URL lleva `?host=<ruta>` en lugar de `localhost:5432`.
"""

from __future__ import annotations

import contextlib
import os
import signal
import sys
import time
from pathlib import Path

import pgserver

REPO = Path(__file__).resolve().parent.parent
PGDATA = REPO / ".local" / "pgdata"


@contextlib.contextmanager
def _silenciar_stdout():
    """Manda a stderr lo que `pgserver`/initdb escriban en stdout.

    Así `db.py url` deja stdout limpio para `DATABASE_URL=$(... url)`.
    """
    guardado = os.dup(1)
    try:
        os.dup2(2, 1)
        yield
    finally:
        os.dup2(guardado, 1)
        os.close(guardado)


def _a_asyncpg(uri: str) -> str:
    return "postgresql+asyncpg://" + uri.removeprefix("postgresql://")


def _pid() -> int | None:
    """PID del postmaster si está vivo, si no None."""
    archivo = PGDATA / "postmaster.pid"
    if not archivo.exists():
        return None
    try:
        pid = int(archivo.read_text().splitlines()[0])
    except (ValueError, IndexError):
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        return pid
    return pid


def _arrancar_y_obtener_url() -> str:
    PGDATA.parent.mkdir(parents=True, exist_ok=True)
    with _silenciar_stdout():
        # cleanup_mode=None => nunca se detiene solo al terminar este proceso.
        servidor = pgserver.get_server(PGDATA, cleanup_mode=None)
        uri = servidor.get_uri()
    return _a_asyncpg(uri)


def cmd_start() -> int:
    nuevo = _pid() is None
    url = _arrancar_y_obtener_url()
    print(f"Postgres {'arrancado' if nuevo else 'ya estaba corriendo'} en {PGDATA}", file=sys.stderr)
    print(url)
    return 0


def cmd_url() -> int:
    print(_arrancar_y_obtener_url())
    return 0


def cmd_status() -> int:
    pid = _pid()
    if pid is None:
        print("Postgres detenido.", file=sys.stderr)
        return 1
    print(f"Postgres corriendo (pid {pid}) en {PGDATA}", file=sys.stderr)
    return 0


def cmd_stop() -> int:
    if _pid() is None:
        print("Postgres ya estaba detenido.", file=sys.stderr)
        return 0

    # Camino normal: cleanup_mode por defecto ('stop') apaga en el último handle.
    with _silenciar_stdout():
        with contextlib.suppress(Exception):
            pgserver.get_server(PGDATA).cleanup()

    for _ in range(40):
        if _pid() is None:
            print("Postgres detenido.", file=sys.stderr)
            return 0
        time.sleep(0.25)

    # `pgserver.cleanup()` a veces no hace nada (PIDs obsoletos en su lista
    # interna); en ese caso matamos el postmaster directamente.
    pid = _pid()
    if pid is not None:
        os.kill(pid, signal.SIGTERM)
        for _ in range(40):
            if _pid() is None:
                print("Postgres detenido (SIGTERM).", file=sys.stderr)
                return 0
            time.sleep(0.25)
        pid = _pid()
        if pid is not None:
            os.kill(pid, signal.SIGKILL)
            print("Postgres detenido (SIGKILL).", file=sys.stderr)
    return 0


COMANDOS = {
    "start": cmd_start,
    "url": cmd_url,
    "stop": cmd_stop,
    "status": cmd_status,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in COMANDOS:
        print(f"Uso: db.py {{{'|'.join(COMANDOS)}}}", file=sys.stderr)
        return 2
    return COMANDOS[sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main())
