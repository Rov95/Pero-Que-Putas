import { calcularLector } from '../store/slices/salaSlice'
import type { RootState } from '../store'
import type { Jugador } from '../tipos/modelos'

export const selectSala = (state: RootState) => state.sala.sala

export const selectLector = (state: RootState): Jugador | null => {
  const sala = state.sala.sala
  return sala ? calcularLector(sala) : null
}

export const selectSoyLector = (state: RootState): boolean => {
  const lector = selectLector(state)
  const miId = state.sesion.usuario?.id
  return Boolean(lector && miId && lector.usuario_id === miId)
}

export const selectSoyAnfitrion = (state: RootState): boolean => {
  const sala = state.sala.sala
  const miId = state.sesion.usuario?.id
  return Boolean(sala && miId && sala.anfitrion_id === miId)
}

export const selectMiJugador = (state: RootState): Jugador | null => {
  const sala = state.sala.sala
  const miId = state.sesion.usuario?.id
  if (!sala || !miId) return null
  return sala.jugadores.find((j) => j.usuario_id === miId) ?? null
}

export const selectJugadoresOrdenadosPorPuntos = (state: RootState): Jugador[] => {
  const sala = state.sala.sala
  if (!sala) return []
  return [...sala.jugadores].sort((a, b) => b.puntos - a.puntos)
}

export const selectVotantesEsperados = (state: RootState): Jugador[] => {
  const sala = state.sala.sala
  if (!sala) return []
  const lector = calcularLector(sala)
  return sala.jugadores.filter((j) => j.conectado && j.usuario_id !== lector?.usuario_id)
}

export const selectJugadoresConectadosCount = (state: RootState): number => {
  const sala = state.sala.sala
  if (!sala) return 0
  return sala.jugadores.filter((j) => j.conectado).length
}
