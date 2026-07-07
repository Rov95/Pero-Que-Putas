import { configureStore } from '@reduxjs/toolkit'
import { describe, expect, it } from 'vitest'
import {
  selectJugadoresOrdenadosPorPuntos,
  selectLector,
  selectSoyAnfitrion,
  selectSoyLector,
  selectVotantesEsperados,
} from '../../seleccionadores/juego'
import constantesReducer from '../../store/slices/constantesSlice'
import puntajesReducer from '../../store/slices/puntajesSlice'
import salaReducer, { sincronizarSala } from '../../store/slices/salaSlice'
import sesionReducer, { restaurarSesion } from '../../store/slices/sesionSlice'
import uiReducer from '../../store/slices/uiSlice'
import type { Sala } from '../../tipos/modelos'

function crearStorePrueba() {
  return configureStore({
    reducer: {
      sala: salaReducer,
      sesion: sesionReducer,
      puntajes: puntajesReducer,
      constantes: constantesReducer,
      ui: uiReducer,
    },
  })
}

function salaDePrueba(overrides: Partial<Sala> = {}): Sala {
  return {
    id: 'sala-1',
    codigo: 'ABCDEF',
    estado: 'en_curso',
    anfitrion_id: 'u1',
    turno_actual: 0,
    creado_en: '2026-01-01T00:00:00Z',
    jugadores: [
      { usuario_id: 'u1', username: 'ana', orden_turno: 0, puntos: 5, conectado: true },
      { usuario_id: 'u2', username: 'beto', orden_turno: 1, puntos: 8, conectado: true },
      { usuario_id: 'u3', username: 'cami', orden_turno: 2, puntos: 1, conectado: false },
    ],
    ...overrides,
  }
}

describe('seleccionadores/juego', () => {
  it('selectLector usa el módulo de turno_actual, incluso cuando supera el nº de jugadores', () => {
    const store = crearStorePrueba()
    store.dispatch(sincronizarSala.fulfilled(salaDePrueba({ turno_actual: 7 }), 'r1', 'ABCDEF'))

    // 7 % 3 = 1 → orden_turno 1 → u2
    expect(selectLector(store.getState())?.usuario_id).toBe('u2')
  })

  it('selectSoyLector es true solo si mi usuario_id coincide con el lector derivado', () => {
    const store = crearStorePrueba()
    store.dispatch(sincronizarSala.fulfilled(salaDePrueba({ turno_actual: 1 }), 'r1', 'ABCDEF'))
    store.dispatch(
      restaurarSesion.fulfilled(
        { id: 'u2', username: 'beto', creado_en: '2026-01-01T00:00:00Z' },
        'req',
      ),
    )

    expect(selectSoyLector(store.getState())).toBe(true)
  })

  it('selectSoyAnfitrion compara contra sala.anfitrion_id', () => {
    const store = crearStorePrueba()
    store.dispatch(sincronizarSala.fulfilled(salaDePrueba(), 'r1', 'ABCDEF'))
    store.dispatch(
      restaurarSesion.fulfilled(
        { id: 'u1', username: 'ana', creado_en: '2026-01-01T00:00:00Z' },
        'req',
      ),
    )

    expect(selectSoyAnfitrion(store.getState())).toBe(true)
  })

  it('selectJugadoresOrdenadosPorPuntos ordena descendente', () => {
    const store = crearStorePrueba()
    store.dispatch(sincronizarSala.fulfilled(salaDePrueba(), 'r1', 'ABCDEF'))

    const orden = selectJugadoresOrdenadosPorPuntos(store.getState()).map((j) => j.usuario_id)
    expect(orden).toEqual(['u2', 'u1', 'u3'])
  })

  it('selectVotantesEsperados excluye al lector y a los desconectados', () => {
    const store = crearStorePrueba()
    // turno_actual=0 → lector = u1
    store.dispatch(sincronizarSala.fulfilled(salaDePrueba({ turno_actual: 0 }), 'r1', 'ABCDEF'))

    const esperados = selectVotantesEsperados(store.getState()).map((j) => j.usuario_id)
    expect(esperados).toEqual(['u2'])
  })
})
