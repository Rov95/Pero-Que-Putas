import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { marcadorApi } from '../../api/marcadorApi'
import { detalleDeError } from '../../tipos/api'
import type { MarcadorFinalEntrada, MarcadorHistoricoEntrada } from '../../tipos/modelos'
import { finalizarPartida, salaActions } from './salaSlice'

interface EstadoPuntajes {
  marcadorFinal: MarcadorFinalEntrada[] | null
  historico: MarcadorHistoricoEntrada[]
  cargandoHistorico: boolean
  errorHistorico: string | null
}

const estadoInicial: EstadoPuntajes = {
  marcadorFinal: null,
  historico: [],
  cargandoHistorico: false,
  errorHistorico: null,
}

export const cargarMarcadorHistorico = createAsyncThunk<
  MarcadorHistoricoEntrada[],
  string | undefined,
  { rejectValue: string }
>('puntajes/cargarMarcadorHistorico', async (usuarioId, { rejectWithValue }) => {
  try {
    return await marcadorApi.obtenerHistorico(usuarioId)
  } catch (error) {
    return rejectWithValue(detalleDeError(error))
  }
})

const puntajesSlice = createSlice({
  name: 'puntajes',
  initialState: estadoInicial,
  reducers: {
    limpiarMarcadorFinal: (state) => {
      state.marcadorFinal = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(salaActions.partidaFinalizada, (state, action) => {
        state.marcadorFinal = action.payload.marcador_final
      })
      .addCase(finalizarPartida.fulfilled, (state, action) => {
        state.marcadorFinal = action.payload.marcador_final
      })
      .addCase(cargarMarcadorHistorico.pending, (state) => {
        state.cargandoHistorico = true
        state.errorHistorico = null
      })
      .addCase(cargarMarcadorHistorico.fulfilled, (state, action) => {
        state.cargandoHistorico = false
        state.historico = action.payload
      })
      .addCase(cargarMarcadorHistorico.rejected, (state, action) => {
        state.cargandoHistorico = false
        state.errorHistorico = action.payload ?? 'Error de conexión con el servidor'
      })
  },
})

export const puntajesActions = puntajesSlice.actions
export default puntajesSlice.reducer
