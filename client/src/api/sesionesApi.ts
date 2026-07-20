import { clienteHttp } from './clienteHttp'
import type { CrearUsuarioBody, SesionCreada } from '../tipos/api'

export const sesionesApi = {
  iniciar: (body: CrearUsuarioBody) => clienteHttp.post<SesionCreada>('/api/sesiones', body),
  cerrar: () => clienteHttp.delete<void>('/api/sesiones/actual'),
}
