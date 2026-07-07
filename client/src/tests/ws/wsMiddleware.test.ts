import { configureStore } from '@reduxjs/toolkit'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import constantesReducer from '../../store/slices/constantesSlice'
import puntajesReducer from '../../store/slices/puntajesSlice'
import salaReducer, { salaActions } from '../../store/slices/salaSlice'
import sesionReducer, { restaurarSesion } from '../../store/slices/sesionSlice'
import uiReducer from '../../store/slices/uiSlice'
import type { CallbacksConexionSala, ConexionSala } from '../../ws/clienteWs'
import { crearWsMiddleware } from '../../ws/wsMiddleware'

vi.mock('../../api/salasApi', () => ({
  salasApi: {
    obtener: vi.fn(async (codigo: string) => ({
      id: 'sala-1',
      codigo,
      estado: 'en_curso',
      anfitrion_id: 'u1',
      turno_actual: 0,
      creado_en: '2026-01-01T00:00:00Z',
      jugadores: [],
    })),
  },
}))

class ConexionSalaFalsa {
  static instancias: ConexionSalaFalsa[] = []
  readonly callbacks: CallbacksConexionSala
  mensajesEnviados: unknown[] = []
  cerrada = false
  codigoConectado: string | null = null
  usuarioIdConectado: string | null = null

  constructor(callbacks: CallbacksConexionSala) {
    this.callbacks = callbacks
    ConexionSalaFalsa.instancias.push(this)
  }

  conectar(codigo: string, usuarioId: string) {
    this.codigoConectado = codigo
    this.usuarioIdConectado = usuarioId
  }

  enviar(sobre: unknown) {
    this.mensajesEnviados.push(sobre)
  }

  cerrar() {
    this.cerrada = true
  }
}

function crearStorePrueba() {
  ConexionSalaFalsa.instancias = []
  const fabrica = (callbacks: CallbacksConexionSala) =>
    new ConexionSalaFalsa(callbacks) as unknown as ConexionSala

  const store = configureStore({
    reducer: {
      sala: salaReducer,
      sesion: sesionReducer,
      puntajes: puntajesReducer,
      constantes: constantesReducer,
      ui: uiReducer,
    },
    middleware: (obtenerDefault) => obtenerDefault().concat(crearWsMiddleware(fabrica)),
  })

  store.dispatch(
    restaurarSesion.fulfilled({ id: 'u1', username: 'ana', creado_en: '2026-01-01T00:00:00Z' }, 'req'),
  )
  return store
}

describe('wsMiddleware', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('conectarWs abre una conexión con el código y el usuario_id de la sesión', () => {
    const store = crearStorePrueba()

    store.dispatch(salaActions.conectarWs('ABCDEF'))

    expect(ConexionSalaFalsa.instancias).toHaveLength(1)
    expect(ConexionSalaFalsa.instancias[0].codigoConectado).toBe('ABCDEF')
    expect(ConexionSalaFalsa.instancias[0].usuarioIdConectado).toBe('u1')
  })

  it('no reintenta tras un cierre 4003 (expulsión)', async () => {
    const store = crearStorePrueba()
    store.dispatch(salaActions.conectarWs('ABCDEF'))
    const conexion = ConexionSalaFalsa.instancias[0]

    conexion.callbacks.onCierre({ codigo: 4003, razon: 'No perteneces a esta sala', intencional: false })

    expect(store.getState().sala.motivoExpulsion).toBe('No perteneces a esta sala')

    await vi.advanceTimersByTimeAsync(20_000)

    expect(ConexionSalaFalsa.instancias).toHaveLength(1)
  })

  it('no reintenta tras un cierre intencional (desconectarWs)', async () => {
    const store = crearStorePrueba()
    store.dispatch(salaActions.conectarWs('ABCDEF'))

    store.dispatch(salaActions.desconectarWs())
    expect(ConexionSalaFalsa.instancias[0].cerrada).toBe(true)

    await vi.advanceTimersByTimeAsync(20_000)

    expect(ConexionSalaFalsa.instancias).toHaveLength(1)
  })

  it('reconecta con backoff tras un cierre no intencional, resincronizando antes de reabrir', async () => {
    const store = crearStorePrueba()
    store.dispatch(salaActions.conectarWs('ABCDEF'))
    const primeraConexion = ConexionSalaFalsa.instancias[0]

    primeraConexion.callbacks.onCierre({ codigo: 1006, razon: '', intencional: false })
    expect(store.getState().sala.conexion).toBe('reconectando')

    // primer reintento: 1000ms
    await vi.advanceTimersByTimeAsync(1000)

    expect(ConexionSalaFalsa.instancias).toHaveLength(2)
    expect(ConexionSalaFalsa.instancias[1].codigoConectado).toBe('ABCDEF')
  })

  it('robarCarta/enviarVoto envían el sobre WS esperado', () => {
    const store = crearStorePrueba()
    store.dispatch(salaActions.conectarWs('ABCDEF'))
    const conexion = ConexionSalaFalsa.instancias[0]

    store.dispatch(salaActions.robarCarta())
    store.dispatch(salaActions.enviarVoto(2))

    expect(conexion.mensajesEnviados).toEqual([
      { evento: 'robar_carta', datos: {} },
      { evento: 'voto', datos: { opcion: 2 } },
    ])
  })
})
