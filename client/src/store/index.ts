import { combineReducers, configureStore } from '@reduxjs/toolkit'
import constantesReducer from './slices/constantesSlice'
import puntajesReducer from './slices/puntajesSlice'
import salaReducer from './slices/salaSlice'
import sesionReducer from './slices/sesionSlice'
import uiReducer from './slices/uiSlice'
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

export type AppDispatch = typeof store.dispatch
