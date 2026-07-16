import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { salasApi } from '../../api/salasApi'
import { detalleDeError, type FinalizarRespuesta } from '../../tipos/api'
import type { DatosResultadoRonda, PreguntaEnRonda, ResumenJugador } from '../../tipos/eventosWs'
import type {
  Jugador,
  MarcadorFinalEntrada,
  OpcionVoto,
  PrediccionClave,
  Sala,
} from '../../tipos/modelos'
import type { RootState } from '../index'

export type EstadoConexionWs = 'desconectado' | 'conectando' | 'conectado' | 'reconectando'

interface EstadoRonda {
  id: string | null
  etapa: 'leyendo' | 'votando' | 'resuelta' | null
  pregunta: PreguntaEnRonda | null
  votosRecibidos: number
  votosEsperados: number
  miVoto: OpcionVoto | null
  miPrediccion: PrediccionClave | null
  resultado: DatosResultadoRonda | null
  desconocida: boolean
}

interface EstadoSalaSlice {
  sala: Sala | null
  cargando: boolean
  error: string | null
  conexion: EstadoConexionWs
  motivoExpulsion: string | null
  ronda: EstadoRonda
  errorJuego: string | null
}

function estadoRondaInicial(): EstadoRonda {
  return {
    id: null,
    etapa: null,
    pregunta: null,
    votosRecibidos: 0,
    votosEsperados: 0,
    miVoto: null,
    miPrediccion: null,
    resultado: null,
    desconocida: false,
  }
}

function estadoInicial(): EstadoSalaSlice {
  return {
    sala: null,
    cargando: false,
    error: null,
    conexion: 'desconectado',
    motivoExpulsion: null,
    ronda: estadoRondaInicial(),
    errorJuego: null,
  }
}

/** Módulo del lector: el mismo cálculo que hace el backend, nunca se asume localmente. */
export function calcularLector(sala: Pick<Sala, 'jugadores' | 'turno_actual'>): Jugador | null {
  if (sala.jugadores.length === 0) return null
  const ordenLector = sala.turno_actual % sala.jugadores.length
  return sala.jugadores.find((j) => j.orden_turno === ordenLector) ?? null
}

export const crearSala = createAsyncThunk<Sala, void, { state: RootState; rejectValue: string }>(
  'sala/crearSala',
  async (_, { getState, rejectWithValue }) => {
    const usuarioId = getState().sesion.usuario?.id
    if (!usuarioId) return rejectWithValue('Debes iniciar sesión primero')
    try {
      return await salasApi.crear({ usuario_id: usuarioId })
    } catch (error) {
      return rejectWithValue(detalleDeError(error))
    }
  },
)

export const crearPractica = createAsyncThunk<
  Sala,
  void,
  { state: RootState; rejectValue: string }
>('sala/crearPractica', async (_, { getState, rejectWithValue }) => {
  const usuarioId = getState().sesion.usuario?.id
  if (!usuarioId) return rejectWithValue('Debes iniciar sesión primero')
  try {
    return await salasApi.crearPractica({ usuario_id: usuarioId })
  } catch (error) {
    return rejectWithValue(detalleDeError(error))
  }
})

export const unirseSala = createAsyncThunk<
  Sala,
  string,
  { state: RootState; rejectValue: string }
>('sala/unirseSala', async (codigo, { getState, rejectWithValue }) => {
  const usuarioId = getState().sesion.usuario?.id
  if (!usuarioId) return rejectWithValue('Debes iniciar sesión primero')
  try {
    return await salasApi.unirse(codigo, { usuario_id: usuarioId })
  } catch (error) {
    return rejectWithValue(detalleDeError(error))
  }
})

export const sincronizarSala = createAsyncThunk<Sala, string, { rejectValue: string }>(
  'sala/sincronizarSala',
  async (codigo, { rejectWithValue }) => {
    try {
      return await salasApi.obtener(codigo)
    } catch (error) {
      return rejectWithValue(detalleDeError(error))
    }
  },
)

export const iniciarPartida = createAsyncThunk<
  Sala,
  void,
  { state: RootState; rejectValue: string }
>('sala/iniciarPartida', async (_, { getState, rejectWithValue }) => {
  const estado = getState()
  const usuarioId = estado.sesion.usuario?.id
  const codigo = estado.sala.sala?.codigo
  if (!usuarioId || !codigo) return rejectWithValue('No hay sala activa')
  try {
    return await salasApi.iniciar(codigo, { usuario_id: usuarioId })
  } catch (error) {
    return rejectWithValue(detalleDeError(error))
  }
})

export const finalizarPartida = createAsyncThunk<
  FinalizarRespuesta,
  void,
  { state: RootState; rejectValue: string }
>('sala/finalizarPartida', async (_, { getState, rejectWithValue }) => {
  const estado = getState()
  const usuarioId = estado.sesion.usuario?.id
  const codigo = estado.sala.sala?.codigo
  if (!usuarioId || !codigo) return rejectWithValue('No hay sala activa')
  try {
    return await salasApi.finalizar(codigo, { usuario_id: usuarioId })
  } catch (error) {
    return rejectWithValue(detalleDeError(error))
  }
})

const salaSlice = createSlice({
  name: 'sala',
  initialState: estadoInicial(),
  reducers: {
    // --- Intenciones WS salientes (interceptadas por wsMiddleware) ---
    conectarWs: (state, _action: PayloadAction<string>) => {
      state.conexion = 'conectando'
    },
    desconectarWs: (state) => {
      state.conexion = 'desconectado'
    },
    robarCarta: () => {},
    enviarPrediccion: (state, action: PayloadAction<PrediccionClave>) => {
      state.ronda.miPrediccion = action.payload
    },
    enviarVoto: (state, action: PayloadAction<OpcionVoto>) => {
      state.ronda.miVoto = action.payload
    },
    siguienteTurno: () => {},

    // --- Eventos WS entrantes (despachados por wsMiddleware) ---
    wsConectado: (state, action: PayloadAction<string>) => {
      state.conexion = 'conectado'
      state.motivoExpulsion = null
      // El snapshot REST se pidió antes de abrir este socket, así que mi propio
      // `conectado` puede seguir en false (el servidor nunca me manda `jugador_unido` a mí mismo).
      const yo = state.sala?.jugadores.find((j) => j.usuario_id === action.payload)
      if (yo) yo.conectado = true
    },
    wsReconectando: (state) => {
      state.conexion = 'reconectando'
    },
    wsDesconectado: (state) => {
      state.conexion = 'desconectado'
    },
    wsExpulsado: (state, action: PayloadAction<string>) => {
      state.sala = null
      state.ronda = estadoRondaInicial()
      state.motivoExpulsion = action.payload
      state.conexion = 'desconectado'
    },
    jugadorUnido: (state, action: PayloadAction<ResumenJugador>) => {
      if (!state.sala) return
      const jugador = state.sala.jugadores.find(
        (j) => j.usuario_id === action.payload.usuario_id,
      )
      if (jugador) {
        jugador.conectado = true
      } else {
        state.sala.jugadores.push({
          usuario_id: action.payload.usuario_id,
          username: action.payload.username,
          orden_turno: null,
          puntos: 0,
          conectado: true,
        })
      }
    },
    jugadorSalio: (state, action: PayloadAction<ResumenJugador>) => {
      const jugador = state.sala?.jugadores.find(
        (j) => j.usuario_id === action.payload.usuario_id,
      )
      if (jugador) jugador.conectado = false
    },
    partidaIniciada: (
      state,
      action: PayloadAction<{
        orden: Array<ResumenJugador & { orden_turno: number }>
        lector: ResumenJugador
      }>,
    ) => {
      if (!state.sala) return
      state.sala.estado = 'en_curso'
      for (const entrada of action.payload.orden) {
        const jugador = state.sala.jugadores.find((j) => j.usuario_id === entrada.usuario_id)
        if (jugador) jugador.orden_turno = entrada.orden_turno
      }
    },
    turnoActual: (
      state,
      action: PayloadAction<{ numero: number; lector: ResumenJugador }>,
    ) => {
      if (state.sala) state.sala.turno_actual = action.payload.numero
      state.ronda = estadoRondaInicial()
    },
    cartaRobada: (
      state,
      action: PayloadAction<{ ronda_id: string; pregunta: PreguntaEnRonda }>,
    ) => {
      state.ronda.id = action.payload.ronda_id
      state.ronda.pregunta = action.payload.pregunta
      state.ronda.etapa = 'leyendo'
      state.ronda.desconocida = false
    },
    prediccionRegistrada: (state) => {
      state.ronda.etapa = 'votando'
    },
    votoRegistrado: (
      state,
      action: PayloadAction<{ votos_recibidos: number; votos_esperados: number }>,
    ) => {
      state.ronda.votosRecibidos = action.payload.votos_recibidos
      state.ronda.votosEsperados = action.payload.votos_esperados
    },
    resultadoRonda: (state, action: PayloadAction<DatosResultadoRonda>) => {
      state.ronda.etapa = 'resuelta'
      state.ronda.resultado = action.payload
      state.ronda.desconocida = false
      if (state.sala) {
        const lector = calcularLector(state.sala)
        if (lector) lector.puntos = action.payload.puntos_lector
      }
    },
    partidaFinalizada: (
      state,
      _action: PayloadAction<{ marcador_final: MarcadorFinalEntrada[] }>,
    ) => {
      if (state.sala) state.sala.estado = 'finalizada'
    },
    errorJuego: (state, action: PayloadAction<string>) => {
      state.errorJuego = action.payload
      if (action.payload !== 'Ya votaste en esta ronda') {
        state.ronda.miVoto = null
        state.ronda.miPrediccion = null
      }
    },
    limpiarErrorJuego: (state) => {
      state.errorJuego = null
    },
    limpiarError: (state) => {
      state.error = null
    },
    limpiarSala: () => estadoInicial(),
  },
  extraReducers: (builder) => {
    builder
      .addCase(crearSala.pending, (state) => {
        state.cargando = true
        state.error = null
      })
      .addCase(crearSala.fulfilled, (state, action) => {
        state.cargando = false
        state.sala = action.payload
      })
      .addCase(crearSala.rejected, (state, action) => {
        state.cargando = false
        state.error = action.payload ?? 'Error de conexión con el servidor'
      })

      .addCase(crearPractica.pending, (state) => {
        state.cargando = true
        state.error = null
      })
      .addCase(crearPractica.fulfilled, (state, action) => {
        state.cargando = false
        state.sala = action.payload
      })
      .addCase(crearPractica.rejected, (state, action) => {
        state.cargando = false
        state.error = action.payload ?? 'Error de conexión con el servidor'
      })

      .addCase(unirseSala.pending, (state) => {
        state.cargando = true
        state.error = null
      })
      .addCase(unirseSala.fulfilled, (state, action) => {
        state.cargando = false
        state.sala = action.payload
      })
      .addCase(unirseSala.rejected, (state, action) => {
        state.cargando = false
        state.error = action.payload ?? 'Error de conexión con el servidor'
      })

      .addCase(sincronizarSala.pending, (state) => {
        state.cargando = true
      })
      .addCase(sincronizarSala.fulfilled, (state, action) => {
        state.cargando = false
        state.error = null
        state.sala = action.payload
        if (action.payload.estado === 'en_curso' && state.ronda.etapa === null) {
          state.ronda.desconocida = true
        }
      })
      .addCase(sincronizarSala.rejected, (state, action) => {
        state.cargando = false
        state.error = action.payload ?? 'Error de conexión con el servidor'
      })

      .addCase(iniciarPartida.pending, (state) => {
        state.cargando = true
        state.error = null
      })
      .addCase(iniciarPartida.fulfilled, (state, action) => {
        state.cargando = false
        state.sala = action.payload
      })
      .addCase(iniciarPartida.rejected, (state, action) => {
        state.cargando = false
        state.error = action.payload ?? 'Error de conexión con el servidor'
      })

      .addCase(finalizarPartida.pending, (state) => {
        state.cargando = true
        state.error = null
      })
      .addCase(finalizarPartida.fulfilled, (state, action) => {
        state.cargando = false
        state.sala = action.payload.sala
      })
      .addCase(finalizarPartida.rejected, (state, action) => {
        state.cargando = false
        state.error = action.payload ?? 'Error de conexión con el servidor'
      })
  },
})

export const salaActions = salaSlice.actions
export default salaSlice.reducer
