import { clienteHttp } from './clienteHttp'
import type { CrearUsuarioBody, SesionCreada } from '../tipos/api'
import type { Usuario } from '../tipos/modelos'

export const usuariosApi = {
  crear: (body: CrearUsuarioBody) => clienteHttp.post<SesionCreada>('/api/usuarios', body),
  obtenerActual: () => clienteHttp.get<Usuario>('/api/usuarios/actual'),
  obtener: (id: string) => clienteHttp.get<Usuario>(`/api/usuarios/${id}`),
}
