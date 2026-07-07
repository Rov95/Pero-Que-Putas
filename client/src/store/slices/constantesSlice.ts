import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { constantesApi } from '../../api/constantesApi'
import { detalleDeError, type PrediccionConstante } from '../../tipos/api'

interface EstadoConstantes {
  predicciones: PrediccionConstante[]
  cargado: boolean
}

const estadoInicial: EstadoConstantes = {
  predicciones: [],
  cargado: false,
}

export const cargarPredicciones = createAsyncThunk<
  PrediccionConstante[],
  void,
  { rejectValue: string }
>('constantes/cargarPredicciones', async (_, { rejectWithValue }) => {
  try {
    return await constantesApi.obtenerPredicciones()
  } catch (error) {
    return rejectWithValue(detalleDeError(error))
  }
})

const constantesSlice = createSlice({
  name: 'constantes',
  initialState: estadoInicial,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(cargarPredicciones.fulfilled, (state, action) => {
      state.predicciones = action.payload
      state.cargado = true
    })
  },
})

export const constantesActions = constantesSlice.actions
export default constantesSlice.reducer
