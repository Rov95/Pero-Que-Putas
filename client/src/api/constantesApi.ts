import { clienteHttp } from './clienteHttp'
import type { PrediccionConstante } from '../tipos/api'

export const constantesApi = {
  obtenerPredicciones: () =>
    clienteHttp.get<PrediccionConstante[]>('/api/constantes/predicciones'),
}
