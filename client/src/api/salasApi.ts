import { clienteHttp } from './clienteHttp'
import type { AccionSalaBody, FinalizarRespuesta } from '../tipos/api'
import type { PuntoJugador, Sala } from '../tipos/modelos'

export const salasApi = {
  crear: (body: AccionSalaBody) => clienteHttp.post<Sala>('/api/salas', body),
  crearPractica: (body: AccionSalaBody) => clienteHttp.post<Sala>('/api/salas/practica', body),
  unirse: (codigo: string, body: AccionSalaBody) =>
    clienteHttp.post<Sala>(`/api/salas/${codigo}/unirse`, body),
  obtener: (codigo: string) => clienteHttp.get<Sala>(`/api/salas/${codigo}`),
  iniciar: (codigo: string, body: AccionSalaBody) =>
    clienteHttp.post<Sala>(`/api/salas/${codigo}/iniciar`, body),
  finalizar: (codigo: string, body: AccionSalaBody) =>
    clienteHttp.post<FinalizarRespuesta>(`/api/salas/${codigo}/finalizar`, body),
  obtenerPuntos: (codigo: string) => clienteHttp.get<PuntoJugador[]>(`/api/salas/${codigo}/puntos`),
  actualizarPuntos: (codigo: string, usuarioId: string, puntos: number) =>
    clienteHttp.put<PuntoJugador>(`/api/salas/${codigo}/puntos/${usuarioId}`, { puntos }),
  borrarPuntos: (codigo: string) => clienteHttp.delete<void>(`/api/salas/${codigo}/puntos`),
}
