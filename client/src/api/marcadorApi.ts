import { clienteHttp } from './clienteHttp'
import type { MarcadorHistoricoEntrada } from '../tipos/modelos'

export const marcadorApi = {
  obtenerHistorico: (usuarioId?: string) =>
    clienteHttp.get<MarcadorHistoricoEntrada[]>('/api/marcador', { usuario_id: usuarioId }),
}
