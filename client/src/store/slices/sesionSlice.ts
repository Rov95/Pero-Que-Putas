import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { usuariosApi } from '../../api/usuariosApi'
import { detalleDeError } from '../../tipos/api'
import type { Usuario } from '../../tipos/modelos'
import { almacenamiento } from '../../utilidades/almacenamiento'

interface EstadoSesion {
  usuario: Usuario | null
  cargando: boolean
  error: string | null
  restaurada: boolean
}

const estadoInicial: EstadoSesion = {
  usuario: null,
  cargando: false,
  error: null,
  restaurada: false,
}

export const crearUsuario = createAsyncThunk<Usuario, string, { rejectValue: string }>(
  'sesion/crearUsuario',
  async (username, { rejectWithValue }) => {
    try {
      return await usuariosApi.crear({ username })
    } catch (error) {
      return rejectWithValue(detalleDeError(error))
    }
  },
)

export const restaurarSesion = createAsyncThunk<Usuario | null>(
  'sesion/restaurarSesion',
  async () => {
    const usuarioId = almacenamiento.obtenerUsuarioId()
    if (!usuarioId) return null
    try {
      return await usuariosApi.obtener(usuarioId)
    } catch {
      almacenamiento.limpiarSesion()
      return null
    }
  },
)

const sesionSlice = createSlice({
  name: 'sesion',
  initialState: estadoInicial,
  reducers: {
    cerrarSesion: (state) => {
      state.usuario = null
      state.error = null
      almacenamiento.limpiarSesion()
    },
    limpiarErrorSesion: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(crearUsuario.pending, (state) => {
        state.cargando = true
        state.error = null
      })
      .addCase(crearUsuario.fulfilled, (state, action: PayloadAction<Usuario>) => {
        state.cargando = false
        state.usuario = action.payload
        almacenamiento.guardarUsuarioId(action.payload.id)
        almacenamiento.guardarUsername(action.payload.username)
      })
      .addCase(crearUsuario.rejected, (state, action) => {
        state.cargando = false
        state.error = action.payload ?? 'Error de conexión con el servidor'
      })
      .addCase(restaurarSesion.pending, (state) => {
        state.cargando = true
      })
      .addCase(restaurarSesion.fulfilled, (state, action: PayloadAction<Usuario | null>) => {
        state.cargando = false
        state.usuario = action.payload
        state.restaurada = true
      })
      .addCase(restaurarSesion.rejected, (state) => {
        state.cargando = false
        state.restaurada = true
      })
  },
})

export const sesionActions = sesionSlice.actions
export default sesionSlice.reducer
