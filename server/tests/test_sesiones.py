import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from httpx_ws import WebSocketDisconnect

from tests.apoyo import conectar_ws, registrar_usuario


async def test_registro_devuelve_token_y_usuario(client: AsyncClient) -> None:
    respuesta = await client.post("/api/usuarios", json={"username": "andres"})
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert "token" in cuerpo
    assert cuerpo["usuario"]["username"] == "andres"
    assert "id" in cuerpo["usuario"]
    assert "creado_en" in cuerpo["usuario"]


async def test_iniciar_sesion(client: AsyncClient) -> None:
    creds = await registrar_usuario(client, "andres")

    respuesta = await client.post("/api/sesiones", json={"username": "andres"})
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["usuario"]["id"] == creds.usuario_id
    assert cuerpo["token"] != creds.token


async def test_iniciar_sesion_case_insensitive(client: AsyncClient) -> None:
    creds = await registrar_usuario(client, "andres")

    respuesta = await client.post("/api/sesiones", json={"username": "ANDRES"})
    assert respuesta.status_code == 201
    assert respuesta.json()["usuario"]["id"] == creds.usuario_id


async def test_iniciar_sesion_usuario_desconocido(client: AsyncClient) -> None:
    respuesta = await client.post("/api/sesiones", json={"username": "fantasma"})
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": "Usuario no encontrado"}


async def test_usuario_actual(client: AsyncClient) -> None:
    creds = await registrar_usuario(client, "andres")

    respuesta = await client.get("/api/usuarios/actual", headers=creds.cabeceras)
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creds.usuario_id
    assert respuesta.json()["username"] == "andres"


async def test_usuario_actual_sin_cabecera(client: AsyncClient) -> None:
    respuesta = await client.get("/api/usuarios/actual")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": "No autenticado"}


async def test_usuario_actual_token_invalido(client: AsyncClient) -> None:
    respuesta = await client.get(
        "/api/usuarios/actual", headers={"Authorization": "Bearer basura"}
    )
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": "Sesión inválida"}


async def test_usuario_actual_token_desconocido(client: AsyncClient) -> None:
    respuesta = await client.get(
        "/api/usuarios/actual",
        headers={"Authorization": "Bearer 00000000-0000-0000-0000-000000000000"},
    )
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": "Sesión inválida"}


async def test_cerrar_sesion_revoca_el_token(client: AsyncClient) -> None:
    creds = await registrar_usuario(client, "andres")

    respuesta = await client.delete("/api/sesiones/actual", headers=creds.cabeceras)
    assert respuesta.status_code == 204

    tras_cierre = await client.get("/api/usuarios/actual", headers=creds.cabeceras)
    assert tras_cierre.status_code == 401

    sala = await client.post("/api/salas", headers=creds.cabeceras)
    assert sala.status_code == 401


async def test_cerrar_sesion_sin_cabecera(client: AsyncClient) -> None:
    respuesta = await client.delete("/api/sesiones/actual")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": "No autenticado"}


async def test_sesiones_multiples_coexisten(client: AsyncClient) -> None:
    creds = await registrar_usuario(client, "andres")
    login = await client.post("/api/sesiones", json={"username": "andres"})
    token_extra = login.json()["token"]

    # Cerrar la sesión del registro no invalida la del login.
    await client.delete("/api/sesiones/actual", headers=creds.cabeceras)

    respuesta = await client.get(
        "/api/usuarios/actual", headers={"Authorization": f"Bearer {token_extra}"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creds.usuario_id


async def test_crear_sala_sin_sesion(client: AsyncClient) -> None:
    respuesta = await client.post("/api/salas")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": "No autenticado"}


async def test_ws_rechaza_token_invalido(client: AsyncClient, app_prueba: FastAPI) -> None:
    creds = await registrar_usuario(client, "andres")
    creada = await client.post("/api/salas", headers=creds.cabeceras)
    codigo = creada.json()["codigo"]

    async with conectar_ws(app_prueba, codigo, "token-basura") as ws:
        with pytest.raises(WebSocketDisconnect) as info:
            await ws.receive_json()
        assert info.value.code == 4001


async def test_ws_rechaza_token_revocado(client: AsyncClient, app_prueba: FastAPI) -> None:
    creds = await registrar_usuario(client, "andres")
    creada = await client.post("/api/salas", headers=creds.cabeceras)
    codigo = creada.json()["codigo"]

    await client.delete("/api/sesiones/actual", headers=creds.cabeceras)

    async with conectar_ws(app_prueba, codigo, creds.token) as ws:
        with pytest.raises(WebSocketDisconnect) as info:
            await ws.receive_json()
        assert info.value.code == 4001
