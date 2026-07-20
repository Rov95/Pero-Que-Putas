from httpx import AsyncClient

from tests.apoyo import Credenciales, registrar_usuario


async def _crear_sala_en_curso(
    client: AsyncClient, n_jugadores: int
) -> tuple[str, list[Credenciales]]:
    jugadores = [await registrar_usuario(client, f"pun{i}") for i in range(n_jugadores)]
    creada = await client.post("/api/salas", headers=jugadores[0].cabeceras)
    codigo = creada.json()["codigo"]
    for jugador in jugadores[1:]:
        await client.post(f"/api/salas/{codigo}/unirse", headers=jugador.cabeceras)
    await client.post(f"/api/salas/{codigo}/iniciar", headers=jugadores[0].cabeceras)
    return codigo, jugadores


async def test_obtener_puntos(client: AsyncClient) -> None:
    codigo, _ = await _crear_sala_en_curso(client, 2)

    respuesta = await client.get(f"/api/salas/{codigo}/puntos")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 2
    assert all(j["puntos"] == 0 for j in cuerpo)


async def test_establecer_puntos(client: AsyncClient) -> None:
    codigo, jugadores = await _crear_sala_en_curso(client, 2)

    respuesta = await client.put(
        f"/api/salas/{codigo}/puntos/{jugadores[0].usuario_id}", json={"puntos": 5}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["puntos"] == 5

    verificacion = await client.get(f"/api/salas/{codigo}/puntos")
    puntos_por_id = {j["usuario_id"]: j["puntos"] for j in verificacion.json()}
    assert puntos_por_id[jugadores[0].usuario_id] == 5
    assert puntos_por_id[jugadores[1].usuario_id] == 0


async def test_reiniciar_puntos(client: AsyncClient) -> None:
    codigo, jugadores = await _crear_sala_en_curso(client, 2)
    await client.put(f"/api/salas/{codigo}/puntos/{jugadores[0].usuario_id}", json={"puntos": 5})
    await client.put(f"/api/salas/{codigo}/puntos/{jugadores[1].usuario_id}", json={"puntos": 3})

    respuesta = await client.delete(f"/api/salas/{codigo}/puntos")
    assert respuesta.status_code == 204

    verificacion = await client.get(f"/api/salas/{codigo}/puntos")
    assert all(j["puntos"] == 0 for j in verificacion.json())


async def test_finalizar_partida_transfiere_a_marcador(client: AsyncClient) -> None:
    codigo, jugadores = await _crear_sala_en_curso(client, 3)
    await client.put(f"/api/salas/{codigo}/puntos/{jugadores[0].usuario_id}", json={"puntos": 5})
    await client.put(f"/api/salas/{codigo}/puntos/{jugadores[1].usuario_id}", json={"puntos": 2})

    respuesta = await client.post(f"/api/salas/{codigo}/finalizar", headers=jugadores[0].cabeceras)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["sala"]["estado"] == "finalizada"
    assert all(j["puntos"] == 0 for j in cuerpo["sala"]["jugadores"])

    marcador_por_id = {m["usuario_id"]: m for m in cuerpo["marcador_final"]}
    assert marcador_por_id[jugadores[0].usuario_id]["puntos_finales"] == 5
    assert marcador_por_id[jugadores[0].usuario_id]["gano"] is True
    assert marcador_por_id[jugadores[1].usuario_id]["gano"] is False
    assert marcador_por_id[jugadores[2].usuario_id]["gano"] is False

    historico = await client.get("/api/marcador")
    assert historico.status_code == 200
    filas = {f["username"]: f for f in historico.json()}
    assert filas["pun0"]["puntos_totales"] == 5
    assert filas["pun0"]["partidas"] == 1
    assert filas["pun0"]["victorias"] == 1
    assert filas["pun1"]["victorias"] == 0


async def test_finalizar_partida_empate_dos_ganadores(client: AsyncClient) -> None:
    codigo, jugadores = await _crear_sala_en_curso(client, 2)
    await client.put(f"/api/salas/{codigo}/puntos/{jugadores[0].usuario_id}", json={"puntos": 3})
    await client.put(f"/api/salas/{codigo}/puntos/{jugadores[1].usuario_id}", json={"puntos": 3})

    respuesta = await client.post(f"/api/salas/{codigo}/finalizar", headers=jugadores[0].cabeceras)
    assert respuesta.status_code == 200
    ganadores = [m for m in respuesta.json()["marcador_final"] if m["gano"]]
    assert len(ganadores) == 2


async def test_finalizar_no_anfitrion(client: AsyncClient) -> None:
    codigo, jugadores = await _crear_sala_en_curso(client, 2)

    respuesta = await client.post(f"/api/salas/{codigo}/finalizar", headers=jugadores[1].cabeceras)
    assert respuesta.status_code == 403


async def test_finalizar_no_en_curso(client: AsyncClient) -> None:
    codigo, jugadores = await _crear_sala_en_curso(client, 2)
    await client.post(f"/api/salas/{codigo}/finalizar", headers=jugadores[0].cabeceras)

    respuesta = await client.post(f"/api/salas/{codigo}/finalizar", headers=jugadores[0].cabeceras)
    assert respuesta.status_code == 409


async def test_marcador_filtra_por_usuario(client: AsyncClient) -> None:
    codigo, jugadores = await _crear_sala_en_curso(client, 2)
    await client.post(f"/api/salas/{codigo}/finalizar", headers=jugadores[0].cabeceras)

    respuesta = await client.get("/api/marcador", params={"usuario_id": jugadores[0].usuario_id})
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["username"] == "pun0"
