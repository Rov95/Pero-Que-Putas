import { configureStore } from '@reduxjs/toolkit'
import { describe, expect, it } from 'vitest'
import salaReducer, {
  crearPractica,
  salaActions,
  sincronizarSala,
} from '../../store/slices/salaSlice'
import type { Sala } from '../../tipos/modelos'

function crearStorePrueba() {
  return configureStore({ reducer: { sala: salaReducer } })
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
      { usuario_id: 'u1', username: 'ana', orden_turno: 0, puntos: 0, conectado: true },
      { usuario_id: 'u2', username: 'beto', orden_turno: 1, puntos: 0, conectado: true },
      { usuario_id: 'u3', username: 'cami', orden_turno: 2, puntos: 0, conectado: true },
    ],
    ...overrides,
  }
}

function sembrarSala(store: ReturnType<typeof crearStorePrueba>, sala: Sala) {
  store.dispatch(sincronizarSala.fulfilled(sala, 'req-1', sala.codigo))
}

describe('salaSlice — mapeo de eventos WS entrantes', () => {
  it('jugadorUnido marca conectado=true a un jugador existente', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba())

    store.dispatch(
      salaActions.jugadorSalio({ usuario_id: 'u2', username: 'beto' }),
    )
    store.dispatch(
      salaActions.jugadorUnido({ usuario_id: 'u2', username: 'beto' }),
    )

    const jugador = store.getState().sala.sala?.jugadores.find((j) => j.usuario_id === 'u2')
    expect(jugador?.conectado).toBe(true)
  })

  it('jugadorUnido agrega un jugador desconocido con valores por defecto (R5)', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba())

    store.dispatch(
      salaActions.jugadorUnido({ usuario_id: 'u4', username: 'dana' }),
    )

    const jugador = store.getState().sala.sala?.jugadores.find((j) => j.usuario_id === 'u4')
    expect(jugador).toEqual({
      usuario_id: 'u4',
      username: 'dana',
      orden_turno: null,
      puntos: 0,
      conectado: true,
    })
  })

  it('jugadorSalio marca conectado=false', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba())

    store.dispatch(salaActions.jugadorSalio({ usuario_id: 'u2', username: 'beto' }))

    const jugador = store.getState().sala.sala?.jugadores.find((j) => j.usuario_id === 'u2')
    expect(jugador?.conectado).toBe(false)
  })

  it('partidaIniciada pone estado en_curso y asigna orden_turno', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba({ estado: 'esperando' }))

    store.dispatch(
      salaActions.partidaIniciada({
        orden: [
          { usuario_id: 'u2', username: 'beto', orden_turno: 0 },
          { usuario_id: 'u1', username: 'ana', orden_turno: 1 },
          { usuario_id: 'u3', username: 'cami', orden_turno: 2 },
        ],
        lector: { usuario_id: 'u2', username: 'beto' },
      }),
    )

    const estado = store.getState().sala
    expect(estado.sala?.estado).toBe('en_curso')
    expect(estado.sala?.jugadores.find((j) => j.usuario_id === 'u2')?.orden_turno).toBe(0)
    expect(estado.sala?.jugadores.find((j) => j.usuario_id === 'u1')?.orden_turno).toBe(1)
  })

  it('turnoActual actualiza turno_actual y resetea la ronda completa', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba())
    store.dispatch(salaActions.cartaRobada({ ronda_id: 'r1', pregunta: { id: 'p1', opcion_1: 'A', opcion_2: 'B' } }))
    store.dispatch(salaActions.enviarVoto(1))

    store.dispatch(salaActions.turnoActual({ numero: 5, lector: { usuario_id: 'u2', username: 'beto' } }))

    const estado = store.getState().sala
    expect(estado.sala?.turno_actual).toBe(5)
    expect(estado.ronda).toEqual({
      id: null,
      etapa: null,
      pregunta: null,
      votosRecibidos: 0,
      votosEsperados: 0,
      miVoto: null,
      miPrediccion: null,
      resultado: null,
      desconocida: false,
    })
  })

  it('cartaRobada guarda la pregunta y pasa a etapa leyendo', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba())

    store.dispatch(
      salaActions.cartaRobada({
        ronda_id: 'r1',
        pregunta: { id: 'p1', opcion_1: 'Playa', opcion_2: 'Montaña' },
      }),
    )

    const { ronda } = store.getState().sala
    expect(ronda.etapa).toBe('leyendo')
    expect(ronda.id).toBe('r1')
    expect(ronda.pregunta).toEqual({ id: 'p1', opcion_1: 'Playa', opcion_2: 'Montaña' })
  })

  it('prediccionRegistrada pasa a etapa votando', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba())
    store.dispatch(salaActions.cartaRobada({ ronda_id: 'r1', pregunta: { id: 'p1', opcion_1: 'A', opcion_2: 'B' } }))

    store.dispatch(salaActions.prediccionRegistrada())

    expect(store.getState().sala.ronda.etapa).toBe('votando')
  })

  it('votoRegistrado actualiza el progreso de votos', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba())

    store.dispatch(salaActions.votoRegistrado({ votos_recibidos: 1, votos_esperados: 2 }))

    const { ronda } = store.getState().sala
    expect(ronda.votosRecibidos).toBe(1)
    expect(ronda.votosEsperados).toBe(2)
  })

  it('resultadoRonda pasa a resuelta y fija los puntos del lector actual', () => {
    const store = crearStorePrueba()
    // turno_actual=0, 3 jugadores → lector = orden_turno 0 = u1
    sembrarSala(store, salaDePrueba({ turno_actual: 0 }))

    store.dispatch(
      salaActions.resultadoRonda({
        votos: [
          { usuario_id: 'u2', username: 'beto', opcion: 1 },
          { usuario_id: 'u3', username: 'cami', opcion: 1 },
        ],
        resultado: 'todos_1',
        prediccion: 'mayoria_1',
        acierto: false,
        puntos_lector: 3,
      }),
    )

    const estado = store.getState().sala
    expect(estado.ronda.etapa).toBe('resuelta')
    expect(estado.ronda.resultado?.acierto).toBe(false)
    expect(estado.sala?.jugadores.find((j) => j.usuario_id === 'u1')?.puntos).toBe(3)
  })

  it('resultadoRonda usa el módulo de turno_actual para localizar al lector (turno_actual > nº jugadores)', () => {
    const store = crearStorePrueba()
    // 3 jugadores, turno_actual=7 → 7 % 3 = 1 → lector = orden_turno 1 = u2
    sembrarSala(store, salaDePrueba({ turno_actual: 7 }))

    store.dispatch(
      salaActions.resultadoRonda({
        votos: [],
        resultado: 'empate',
        prediccion: 'todos_1',
        acierto: false,
        puntos_lector: 1,
      }),
    )

    const jugadores = store.getState().sala.sala?.jugadores
    expect(jugadores?.find((j) => j.usuario_id === 'u2')?.puntos).toBe(1)
    expect(jugadores?.find((j) => j.usuario_id === 'u1')?.puntos).toBe(0)
  })

  it('wsConectado marca mi propio jugador como conectado (el snapshot REST se pidió antes de abrir mi socket)', () => {
    const store = crearStorePrueba()
    sembrarSala(
      store,
      salaDePrueba({
        jugadores: [
          { usuario_id: 'u1', username: 'ana', orden_turno: 0, puntos: 0, conectado: false },
          { usuario_id: 'u2', username: 'beto', orden_turno: 1, puntos: 0, conectado: true },
          { usuario_id: 'u3', username: 'cami', orden_turno: 2, puntos: 0, conectado: true },
        ],
      }),
    )

    store.dispatch(salaActions.wsConectado('u1'))

    const jugador = store.getState().sala.sala?.jugadores.find((j) => j.usuario_id === 'u1')
    expect(jugador?.conectado).toBe(true)
    expect(store.getState().sala.conexion).toBe('conectado')
  })

  it('partidaFinalizada marca la sala como finalizada', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba())

    store.dispatch(salaActions.partidaFinalizada({ marcador_final: [] }))

    expect(store.getState().sala.sala?.estado).toBe('finalizada')
  })

  it('errorJuego limpia miVoto/miPrediccion salvo cuando el detalle es "Ya votaste en esta ronda"', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba())
    store.dispatch(salaActions.enviarVoto(2))

    store.dispatch(salaActions.errorJuego('Ya votaste en esta ronda'))
    expect(store.getState().sala.ronda.miVoto).toBe(2)
    expect(store.getState().sala.errorJuego).toBe('Ya votaste en esta ronda')

    store.dispatch(salaActions.enviarPrediccion('mayoria_1'))
    store.dispatch(salaActions.errorJuego('Predicción inválida'))
    expect(store.getState().sala.ronda.miVoto).toBeNull()
    expect(store.getState().sala.ronda.miPrediccion).toBeNull()
  })

  it('wsExpulsado limpia sala y ronda, y guarda el motivo', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba())

    store.dispatch(salaActions.wsExpulsado('No perteneces a esta sala'))

    const estado = store.getState().sala
    expect(estado.sala).toBeNull()
    expect(estado.motivoExpulsion).toBe('No perteneces a esta sala')
    expect(estado.conexion).toBe('desconectado')
  })

  it('sincronizarSala.fulfilled marca ronda.desconocida=true si la sala está en_curso y no hay ronda conocida', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba({ estado: 'en_curso' }))

    expect(store.getState().sala.ronda.desconocida).toBe(true)
  })

  it('sincronizarSala.fulfilled NO pisa una ronda ya conocida', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba({ estado: 'en_curso' }))
    store.dispatch(
      salaActions.cartaRobada({ ronda_id: 'r1', pregunta: { id: 'p1', opcion_1: 'A', opcion_2: 'B' } }),
    )

    sembrarSala(store, salaDePrueba({ estado: 'en_curso' }))

    expect(store.getState().sala.ronda.desconocida).toBe(false)
    expect(store.getState().sala.ronda.etapa).toBe('leyendo')
  })

  it('secuencia completa de una ronda: robar → predicción → votos → resultado → siguiente turno', () => {
    const store = crearStorePrueba()
    sembrarSala(store, salaDePrueba({ turno_actual: 0 }))

    store.dispatch(
      salaActions.cartaRobada({ ronda_id: 'r1', pregunta: { id: 'p1', opcion_1: 'A', opcion_2: 'B' } }),
    )
    expect(store.getState().sala.ronda.etapa).toBe('leyendo')

    store.dispatch(salaActions.enviarPrediccion('mayoria_1'))
    store.dispatch(salaActions.prediccionRegistrada())
    expect(store.getState().sala.ronda.etapa).toBe('votando')
    expect(store.getState().sala.ronda.miPrediccion).toBe('mayoria_1')

    store.dispatch(salaActions.enviarVoto(1))
    store.dispatch(salaActions.votoRegistrado({ votos_recibidos: 1, votos_esperados: 2 }))
    store.dispatch(salaActions.votoRegistrado({ votos_recibidos: 2, votos_esperados: 2 }))
    store.dispatch(
      salaActions.resultadoRonda({
        votos: [
          { usuario_id: 'u2', username: 'beto', opcion: 1 },
          { usuario_id: 'u3', username: 'cami', opcion: 1 },
        ],
        resultado: 'todos_1',
        prediccion: 'mayoria_1',
        acierto: true,
        puntos_lector: 1,
      }),
    )
    expect(store.getState().sala.ronda.etapa).toBe('resuelta')
    expect(store.getState().sala.ronda.resultado?.acierto).toBe(true)
    expect(store.getState().sala.sala?.jugadores.find((j) => j.usuario_id === 'u1')?.puntos).toBe(1)

    store.dispatch(salaActions.siguienteTurno())
    store.dispatch(salaActions.turnoActual({ numero: 1, lector: { usuario_id: 'u2', username: 'beto' } }))
    expect(store.getState().sala.sala?.turno_actual).toBe(1)
    expect(store.getState().sala.ronda.etapa).toBeNull()
  })
})

describe('salaSlice — crearPractica', () => {
  it('pending activa cargando', () => {
    const store = crearStorePrueba()

    store.dispatch(crearPractica.pending('req-1', undefined))

    expect(store.getState().sala.cargando).toBe(true)
  })

  it('fulfilled asigna state.sala', () => {
    const store = crearStorePrueba()
    const sala = salaDePrueba()

    store.dispatch(crearPractica.fulfilled(sala, 'req-1', undefined))

    expect(store.getState().sala.sala).toEqual(sala)
    expect(store.getState().sala.cargando).toBe(false)
  })

  it('rejected deja sala=null y guarda el error', () => {
    const store = crearStorePrueba()

    store.dispatch(
      crearPractica.rejected(null, 'req-1', undefined, 'No hay preguntas disponibles'),
    )

    const estado = store.getState().sala
    expect(estado.sala).toBeNull()
    expect(estado.error).toBe('No hay preguntas disponibles')
    expect(estado.cargando).toBe(false)
  })
})
