import { clienteHttp } from './clienteHttp'
import type { CrearPreguntaBody, OpcionesPregunta, ParametrosPaginacion } from '../tipos/api'
import type { Pregunta } from '../tipos/modelos'

export const preguntasApi = {
  listar: (params?: ParametrosPaginacion) =>
    clienteHttp.get<Pregunta[]>('/api/preguntas', params as Record<string, number | undefined>),
  crear: (body: CrearPreguntaBody) => clienteHttp.post<Pregunta>('/api/preguntas', body),
  obtener: (id: string) => clienteHttp.get<Pregunta>(`/api/preguntas/${id}`),
  actualizar: (id: string, body: CrearPreguntaBody) =>
    clienteHttp.put<Pregunta>(`/api/preguntas/${id}`, body),
  obtenerOpciones: (id: string) =>
    clienteHttp.get<OpcionesPregunta>(`/api/preguntas/${id}/opciones`),
  actualizarOpciones: (id: string, body: OpcionesPregunta) =>
    clienteHttp.put<OpcionesPregunta>(`/api/preguntas/${id}/opciones`, body),
  eliminar: (id: string) => clienteHttp.delete<void>(`/api/preguntas/${id}`),
}
