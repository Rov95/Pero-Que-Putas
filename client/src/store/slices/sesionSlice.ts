import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { sesionesApi } from '../../api/sesionesApi'
import { usuariosApi } from '../../api/usuariosApi'
import { datosDeError, type SesionCreada } from '../../tipos/api'
import type { Usuario } from '../../tipos/modelos'
import { almacenamiento } from '../../utilidades/almacenamiento'
import { salaActions } from './salaSlice'

interface EstadoSesion {
  usuario: Usuario | null
  cargando: boolean
  error: string | null
  errorEstado: number | null
  restaurada: boolean
}

const estadoInicial: EstadoSesion = {
  usuario: null,
  cargando: false,
  error: null,
  errorEstado: null,
  restaurada: false,
}

type RechazoSesion = { detalle: string; status: number }

export const crearUsuario = createAsyncThunk<SesionCreada, string, { rejectValue: RechazoSesion }>(
  'sesion/crearUsuario',
  async (username, { rejectWithValue }) => {
    try {
      return await usuariosApi.crear({ username })
    } catch (error) {
      return rejectWithValue(datosDeError(error))
    }
  },
)

export const iniciarSesion = createAsyncThunk<SesionCreada, string, { rejectValue: RechazoSesion }>(
  'sesion/iniciarSesion',
  async (username, { rejectWithValue }) => {
    try {
      return await sesionesApi.iniciar({ username })
    } catch (error) {
      return rejectWithValue(datosDeError(error))
    }
  },
)

export const restaurarSesion = createAsyncThunk<Usuario | null>(
  'sesion/restaurarSesion',
  async () => {
    const token = almacenamiento.obtenerToken()
    if (!token) return null
    try {
      return await usuariosApi.obtenerActual()
    } catch {
      almacenamiento.limpiarSesion()
      return null
    }
  },
)

export const cerrarSesion = createAsyncThunk<void, void>(
  'sesion/cerrarSesion',
  async (_, { dispatch }) => {
    // Primero se corta el WS y se limpia la sala (el middleware aún necesita el usuario
    // en el estado para su lógica de reconexión); después se revoca el token en el servidor.
    dispatch(salaActions.desconectarWs())
    dispatch(salaActions.limpiarSala())
    try {
      await sesionesApi.cerrar()
    } catch {
      // mejor esfuerzo: la sesión local se cierra aunque el servidor no responda
    }
    almacenamiento.limpiarSesion()
  },
)

function guardarCredenciales(payload: SesionCreada): void {
  almacenamiento.guardarUsuarioId(payload.usuario.id)
  almacenamiento.guardarUsername(payload.usuario.username)
  almacenamiento.guardarToken(payload.token)
}

const sesionSlice = createSlice({
  name: 'sesion',
  initialState: estadoInicial,
  reducers: {
    // El servidor respondió 401: el token ya no vale y se descarta la sesión local.
    sesionExpirada: (state) => {
      state.usuario = null
      state.error = null
      state.errorEstado = null
      almacenamiento.limpiarSesion()
    },
    limpiarErrorSesion: (state) => {
      state.error = null
      state.errorEstado = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(crearUsuario.pending, (state) => {
        state.cargando = true
        state.error = null
        state.errorEstado = null
      })
      .addCase(crearUsuario.fulfilled, (state, action: PayloadAction<SesionCreada>) => {
        state.cargando = false
        state.usuario = action.payload.usuario
        guardarCredenciales(action.payload)
      })
      .addCase(crearUsuario.rejected, (state, action) => {
        state.cargando = false
        state.error = action.payload?.detalle ?? 'Error de conexión con el servidor'
        state.errorEstado = action.payload?.status ?? null
      })
      .addCase(iniciarSesion.pending, (state) => {
        state.cargando = true
        state.error = null
        state.errorEstado = null
      })
      .addCase(iniciarSesion.fulfilled, (state, action: PayloadAction<SesionCreada>) => {
        state.cargando = false
        state.usuario = action.payload.usuario
        guardarCredenciales(action.payload)
      })
      .addCase(iniciarSesion.rejected, (state, action) => {
        state.cargando = false
        state.error = action.payload?.detalle ?? 'Error de conexión con el servidor'
        state.errorEstado = action.payload?.status ?? null
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
      .addCase(cerrarSesion.pending, (state) => {
        state.cargando = true
      })
      .addCase(cerrarSesion.fulfilled, (state) => {
        state.cargando = false
        state.usuario = null
        state.error = null
        state.errorEstado = null
      })
      .addCase(cerrarSesion.rejected, (state) => {
        // El thunk nunca relanza errores de red, pero por si acaso: cerrar igual.
        state.cargando = false
        state.usuario = null
      })
  },
})

export const sesionActions = sesionSlice.actions
export default sesionSlice.reducer
