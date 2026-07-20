import { combineReducers, configureStore } from '@reduxjs/toolkit'
import constantesReducer from './slices/constantesSlice'
import puntajesReducer from './slices/puntajesSlice'
import salaReducer from './slices/salaSlice'
import sesionReducer, { sesionActions } from './slices/sesionSlice'
import uiReducer from './slices/uiSlice'
import { establecerManejador401 } from '../api/clienteHttp'
import { crearWsMiddleware } from '../ws/wsMiddleware'

const rootReducer = combineReducers({
  sesion: sesionReducer,
  sala: salaReducer,
  puntajes: puntajesReducer,
  constantes: constantesReducer,
  ui: uiReducer,
})

// Se deriva de rootReducer (no de `store.getState`) para evitar una referencia
// circular: el middleware de WS necesita el tipo RootState y el store incluye ese middleware.
export type RootState = ReturnType<typeof rootReducer>

export const store = configureStore({
  reducer: rootReducer,
  middleware: (obtenerMiddlewareDefault) =>
    obtenerMiddlewareDefault().concat(crearWsMiddleware()),
})

// Cualquier 401 del servidor (token revocado/expirado) descarta la sesión local:
// los guards de las páginas redirigen solos al registro.
establecerManejador401(() => {
  store.dispatch(sesionActions.sesionExpirada())
})

export type AppDispatch = typeof store.dispatch
