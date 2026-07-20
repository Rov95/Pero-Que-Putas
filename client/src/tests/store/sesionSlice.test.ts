import { configureStore } from '@reduxjs/toolkit'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { sesionesApi } from '../../api/sesionesApi'
import { usuariosApi } from '../../api/usuariosApi'
import salaReducer, { sincronizarSala } from '../../store/slices/salaSlice'
import sesionReducer, {
  cerrarSesion,
  crearUsuario,
  iniciarSesion,
  restaurarSesion,
  sesionActions,
} from '../../store/slices/sesionSlice'
import { ErrorApi } from '../../tipos/api'
import type { Sala, Usuario } from '../../tipos/modelos'
import { almacenamiento } from '../../utilidades/almacenamiento'

vi.mock('../../api/usuariosApi', () => ({
  usuariosApi: {
    crear: vi.fn(),
    obtenerActual: vi.fn(),
    obtener: vi.fn(),
  },
}))

vi.mock('../../api/sesionesApi', () => ({
  sesionesApi: {
    iniciar: vi.fn(),
    cerrar: vi.fn(),
  },
}))

const usuarioPrueba: Usuario = { id: 'u1', username: 'ana', creado_en: '2026-01-01T00:00:00Z' }

function salaDePrueba(): Sala {
  return {
    id: 'sala-1',
    codigo: 'ABCDEF',
    estado: 'esperando',
    anfitrion_id: 'u1',
    turno_actual: 0,
    creado_en: '2026-01-01T00:00:00Z',
    jugadores: [],
  }
}

function crearStorePrueba() {
  return configureStore({ reducer: { sesion: sesionReducer, sala: salaReducer } })
}

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

describe('sesionSlice — crearUsuario', () => {
  it('guarda usuario, id, username y token al registrarse', async () => {
    vi.mocked(usuariosApi.crear).mockResolvedValue({ token: 'tok-1', usuario: usuarioPrueba })
    const store = crearStorePrueba()

    await store.dispatch(crearUsuario('ana'))

    expect(store.getState().sesion.usuario).toEqual(usuarioPrueba)
    expect(almacenamiento.obtenerToken()).toBe('tok-1')
    expect(almacenamiento.obtenerUsuarioId()).toBe('u1')
    expect(almacenamiento.obtenerUsername()).toBe('ana')
  })

  it('un 409 deja el detalle y el status para ofrecer iniciar sesión', async () => {
    vi.mocked(usuariosApi.crear).mockRejectedValue(new ErrorApi('Ese nombre ya está en uso', 409))
    const store = crearStorePrueba()

    await store.dispatch(crearUsuario('ana'))

    const estado = store.getState().sesion
    expect(estado.usuario).toBeNull()
    expect(estado.error).toBe('Ese nombre ya está en uso')
    expect(estado.errorEstado).toBe(409)
  })
})

describe('sesionSlice — iniciarSesion', () => {
  it('guarda usuario y token al entrar con un nombre existente', async () => {
    vi.mocked(sesionesApi.iniciar).mockResolvedValue({ token: 'tok-2', usuario: usuarioPrueba })
    const store = crearStorePrueba()

    await store.dispatch(iniciarSesion('ana'))

    expect(store.getState().sesion.usuario).toEqual(usuarioPrueba)
    expect(almacenamiento.obtenerToken()).toBe('tok-2')
  })

  it('un 404 deja el error de usuario no encontrado', async () => {
    vi.mocked(sesionesApi.iniciar).mockRejectedValue(new ErrorApi('Usuario no encontrado', 404))
    const store = crearStorePrueba()

    await store.dispatch(iniciarSesion('fantasma'))

    const estado = store.getState().sesion
    expect(estado.usuario).toBeNull()
    expect(estado.error).toBe('Usuario no encontrado')
    expect(estado.errorEstado).toBe(404)
  })
})

describe('sesionSlice — restaurarSesion', () => {
  it('sin token guardado no llama a la API y queda restaurada sin usuario', async () => {
    const store = crearStorePrueba()

    await store.dispatch(restaurarSesion())

    expect(usuariosApi.obtenerActual).not.toHaveBeenCalled()
    expect(store.getState().sesion.usuario).toBeNull()
    expect(store.getState().sesion.restaurada).toBe(true)
  })

  it('con token válido restaura el usuario actual', async () => {
    almacenamiento.guardarToken('tok-1')
    vi.mocked(usuariosApi.obtenerActual).mockResolvedValue(usuarioPrueba)
    const store = crearStorePrueba()

    await store.dispatch(restaurarSesion())

    expect(store.getState().sesion.usuario).toEqual(usuarioPrueba)
    expect(store.getState().sesion.restaurada).toBe(true)
  })

  it('con token rechazado limpia el almacenamiento', async () => {
    almacenamiento.guardarToken('tok-muerto')
    vi.mocked(usuariosApi.obtenerActual).mockRejectedValue(new ErrorApi('Sesión inválida', 401))
    const store = crearStorePrueba()

    await store.dispatch(restaurarSesion())

    expect(store.getState().sesion.usuario).toBeNull()
    expect(almacenamiento.obtenerToken()).toBeNull()
  })
})

describe('sesionSlice — cerrarSesion', () => {
  async function sembrarSesionConSala() {
    vi.mocked(usuariosApi.crear).mockResolvedValue({ token: 'tok-1', usuario: usuarioPrueba })
    const store = crearStorePrueba()
    await store.dispatch(crearUsuario('ana'))
    store.dispatch(sincronizarSala.fulfilled(salaDePrueba(), 'req-1', 'ABCDEF'))
    almacenamiento.guardarSalaCodigo('ABCDEF')
    return store
  }

  it('revoca el token en el servidor y limpia sesión, sala y almacenamiento', async () => {
    vi.mocked(sesionesApi.cerrar).mockResolvedValue(undefined)
    const store = await sembrarSesionConSala()

    await store.dispatch(cerrarSesion())

    expect(sesionesApi.cerrar).toHaveBeenCalledOnce()
    expect(store.getState().sesion.usuario).toBeNull()
    expect(store.getState().sala.sala).toBeNull()
    expect(store.getState().sala.conexion).toBe('desconectado')
    expect(almacenamiento.obtenerToken()).toBeNull()
    expect(almacenamiento.obtenerUsuarioId()).toBeNull()
    expect(almacenamiento.obtenerUsername()).toBeNull()
    expect(almacenamiento.obtenerSalaCodigo()).toBeNull()
  })

  it('cierra la sesión local aunque el servidor falle (mejor esfuerzo)', async () => {
    vi.mocked(sesionesApi.cerrar).mockRejectedValue(new ErrorApi('Sesión inválida', 401))
    const store = await sembrarSesionConSala()

    await store.dispatch(cerrarSesion())

    expect(store.getState().sesion.usuario).toBeNull()
    expect(almacenamiento.obtenerToken()).toBeNull()
  })
})

describe('sesionSlice — sesionExpirada', () => {
  it('descarta usuario y almacenamiento ante un 401 global', async () => {
    vi.mocked(usuariosApi.crear).mockResolvedValue({ token: 'tok-1', usuario: usuarioPrueba })
    const store = crearStorePrueba()
    await store.dispatch(crearUsuario('ana'))

    store.dispatch(sesionActions.sesionExpirada())

    expect(store.getState().sesion.usuario).toBeNull()
    expect(almacenamiento.obtenerToken()).toBeNull()
  })
})
