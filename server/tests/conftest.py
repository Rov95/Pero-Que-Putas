import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pgserver
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 - registers all models on Base.metadata
from app.database import Base, obtener_sesion
from app.main import create_app


@pytest.fixture(scope="session")
def database_url() -> str:
    pgdata = Path(tempfile.mkdtemp(prefix="pero-que-putas-pgtest-"))
    server = pgserver.get_server(pgdata, cleanup_mode=None)
    uri = server.get_uri()
    yield f"postgresql+asyncpg://{uri.removeprefix('postgresql://')}"
    server.cleanup()


@pytest.fixture(scope="session")
async def engine(database_url: str):
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def limpiar_bd(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        for tabla in reversed(Base.metadata.sorted_tables):
            await conn.execute(tabla.delete())
    yield


@pytest.fixture
def app_prueba(engine: AsyncEngine, limpiar_bd: None) -> FastAPI:
    app = create_app()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _obtener_sesion_prueba() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[obtener_sesion] = _obtener_sesion_prueba
    return app


@pytest.fixture
async def client(app_prueba: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app_prueba)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
