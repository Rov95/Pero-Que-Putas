import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

export type TipoNotificacion = 'error' | 'exito' | 'info'

export interface Notificacion {
  id: string
  tipo: TipoNotificacion
  mensaje: string
}

interface EstadoUi {
  notificaciones: Notificacion[]
}

const estadoInicial: EstadoUi = {
  notificaciones: [],
}

const uiSlice = createSlice({
  name: 'ui',
  initialState: estadoInicial,
  reducers: {
    notificar: {
      reducer: (state, action: PayloadAction<Notificacion>) => {
        state.notificaciones.push(action.payload)
      },
      prepare: (mensaje: string, tipo: TipoNotificacion = 'info') => ({
        payload: { id: crypto.randomUUID(), tipo, mensaje },
      }),
    },
    descartar: (state, action: PayloadAction<string>) => {
      state.notificaciones = state.notificaciones.filter((n) => n.id !== action.payload)
    },
  },
})

export const uiActions = uiSlice.actions
export default uiSlice.reducer
