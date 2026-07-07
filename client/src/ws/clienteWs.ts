import { urlWsSala } from '../api/clienteHttp'
import type { EventoCliente, EventoServidor } from '../tipos/eventosWs'

export interface CierreConexionSala {
  codigo: number
  razon: string
  intencional: boolean
}

export interface CallbacksConexionSala {
  onAbrir: () => void
  onMensaje: (evento: EventoServidor) => void
  onCierre: (detalle: CierreConexionSala) => void
}

/** Dueña de un WebSocket de sala. Inyectable para tests (no abre sockets reales en ellos). */
export class ConexionSala {
  private socket: WebSocket | null = null
  private cerradoIntencionalmente = false
  private readonly callbacks: CallbacksConexionSala

  constructor(callbacks: CallbacksConexionSala) {
    this.callbacks = callbacks
  }

  conectar(codigo: string, usuarioId: string): void {
    this.cerradoIntencionalmente = false
    const socket = new WebSocket(urlWsSala(codigo, usuarioId))

    socket.onopen = () => {
      this.callbacks.onAbrir()
    }

    socket.onmessage = (evento: MessageEvent<string>) => {
      let sobre: { evento?: unknown; datos?: unknown }
      try {
        sobre = JSON.parse(evento.data)
      } catch {
        console.warn('Mensaje WS no es JSON válido', evento.data)
        return
      }
      if (typeof sobre.evento !== 'string') {
        console.warn('Mensaje WS sin campo "evento"', sobre)
        return
      }
      this.callbacks.onMensaje(sobre as EventoServidor)
    }

    socket.onclose = (evento: CloseEvent) => {
      this.callbacks.onCierre({
        codigo: evento.code,
        razon: evento.reason,
        intencional: this.cerradoIntencionalmente,
      })
    }

    this.socket = socket
  }

  enviar(sobre: EventoCliente): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(sobre))
    }
  }

  cerrar(): void {
    this.cerradoIntencionalmente = true
    this.socket?.close()
    this.socket = null
  }
}
