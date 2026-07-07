import { clienteHttp } from './clienteHttp'
import type { CrearUsuarioBody } from '../tipos/api'
import type { Usuario } from '../tipos/modelos'

export const usuariosApi = {
  crear: (body: CrearUsuarioBody) => clienteHttp.post<Usuario>('/api/usuarios', body),
  obtener: (id: string) => clienteHttp.get<Usuario>(`/api/usuarios/${id}`),
}
