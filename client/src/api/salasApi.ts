import { clienteHttp } from './clienteHttp'
import type { FinalizarRespuesta } from '../tipos/api'
import type { PuntoJugador, Sala } from '../tipos/modelos'

export const salasApi = {
  crear: () => clienteHttp.post<Sala>('/api/salas'),
  crearPractica: () => clienteHttp.post<Sala>('/api/salas/practica'),
  unirse: (codigo: string) => clienteHttp.post<Sala>(`/api/salas/${codigo}/unirse`),
  obtener: (codigo: string) => clienteHttp.get<Sala>(`/api/salas/${codigo}`),
  iniciar: (codigo: string) => clienteHttp.post<Sala>(`/api/salas/${codigo}/iniciar`),
  finalizar: (codigo: string) =>
    clienteHttp.post<FinalizarRespuesta>(`/api/salas/${codigo}/finalizar`),
  obtenerPuntos: (codigo: string) => clienteHttp.get<PuntoJugador[]>(`/api/salas/${codigo}/puntos`),
  actualizarPuntos: (codigo: string, usuarioId: string, puntos: number) =>
    clienteHttp.put<PuntoJugador>(`/api/salas/${codigo}/puntos/${usuarioId}`, { puntos }),
  borrarPuntos: (codigo: string) => clienteHttp.delete<void>(`/api/salas/${codigo}/puntos`),
}
