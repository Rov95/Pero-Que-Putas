import type { Middleware, ThunkDispatch, UnknownAction } from '@reduxjs/toolkit'
import type { RootState } from '../store'
import { salaActions, sincronizarSala } from '../store/slices/salaSlice'
import { sesionActions } from '../store/slices/sesionSlice'
import type { EventoServidor } from '../tipos/eventosWs'
import { almacenamiento } from '../utilidades/almacenamiento'
import { ConexionSala, type CallbacksConexionSala } from './clienteWs'

const RETRASOS_RECONEXION_MS = [1000, 2000, 4000, 8000, 10000]

export type FabricaConexionSala = (callbacks: CallbacksConexionSala) => ConexionSala

const fabricaPorDefecto: FabricaConexionSala = (callbacks) => new ConexionSala(callbacks)

// Se construye el tipo de dispatch de forma independiente a `AppDispatch` (que se deriva
// de `store`) para no crear una referencia circular: este middleware se registra al crear `store`.
type DispatchConThunks = ThunkDispatch<RootState, unknown, UnknownAction>

export function crearWsMiddleware(
  fabricaConexion: FabricaConexionSala = fabricaPorDefecto,
): Middleware<Record<string, never>, RootState, DispatchConThunks> {
  return (store) => {
    let conexion: ConexionSala | null = null
    let codigoActual: string | null = null
    let intentosReconexion = 0
    let temporizadorReconexion: ReturnType<typeof setTimeout> | null = null

    const limpiarTemporizador = () => {
      if (temporizadorReconexion !== null) {
        clearTimeout(temporizadorReconexion)
        temporizadorReconexion = null
      }
    }

    const manejarMensaje = (sobre: EventoServidor) => {
      switch (sobre.evento) {
        case 'jugador_unido':
          store.dispatch(salaActions.jugadorUnido(sobre.datos))
          break
        case 'jugador_salio':
          store.dispatch(salaActions.jugadorSalio(sobre.datos))
          break
        case 'partida_iniciada':
          store.dispatch(salaActions.partidaIniciada(sobre.datos))
          break
        case 'turno_actual':
          store.dispatch(salaActions.turnoActual(sobre.datos))
          break
        case 'carta_robada':
          store.dispatch(salaActions.cartaRobada(sobre.datos))
          break
        case 'prediccion_registrada':
          store.dispatch(salaActions.prediccionRegistrada())
          break
        case 'voto_registrado':
          store.dispatch(salaActions.votoRegistrado(sobre.datos))
          break
        case 'resultado_ronda':
          store.dispatch(salaActions.resultadoRonda(sobre.datos))
          break
        case 'partida_finalizada':
          store.dispatch(salaActions.partidaFinalizada(sobre.datos))
          break
        case 'error':
          store.dispatch(salaActions.errorJuego(sobre.datos.detalle))
          break
        default: {
          const _evento: never = sobre
          console.warn('Evento WS desconocido, se descarta', _evento)
        }
      }
    }

    const abrirConexion = (codigo: string) => {
      const usuarioId = store.getState().sesion.usuario?.id
      const token = almacenamiento.obtenerToken()
      if (!usuarioId || !token) return

      conexion = fabricaConexion({
        onAbrir: () => {
          intentosReconexion = 0
          store.dispatch(salaActions.wsConectado(usuarioId))
        },
        onMensaje: manejarMensaje,
        onCierre: ({ codigo: codigoCierre, razon, intencional }) => {
          if (intencional) return

          if (codigoCierre === 4001) {
            // Token revocado/expirado: la sesión entera dejó de valer, no solo el socket.
            codigoActual = null
            store.dispatch(sesionActions.sesionExpirada())
            store.dispatch(salaActions.wsExpulsado(razon || 'Tu sesión ya no es válida'))
            return
          }

          if (codigoCierre === 4003) {
            codigoActual = null
            store.dispatch(
              salaActions.wsExpulsado(razon || 'Has sido desconectado de la sala'),
            )
            return
          }

          store.dispatch(salaActions.wsReconectando())
          programarReconexion()
        },
      })
      conexion.conectar(codigo, token)
    }

    const programarReconexion = () => {
      if (!codigoActual) return
      const retraso =
        RETRASOS_RECONEXION_MS[
          Math.min(intentosReconexion, RETRASOS_RECONEXION_MS.length - 1)
        ]
      intentosReconexion += 1
      limpiarTemporizador()
      temporizadorReconexion = setTimeout(() => {
        void reconectarConResync()
      }, retraso)
    }

    const reconectarConResync = async () => {
      const codigo = codigoActual
      if (!codigo) return
      await store.dispatch(sincronizarSala(codigo))
      if (codigoActual === codigo) abrirConexion(codigo)
    }

    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState !== 'visible' || !codigoActual) return
        const estadoConexion = store.getState().sala.conexion
        if (estadoConexion === 'conectado' || estadoConexion === 'conectando') return
        limpiarTemporizador()
        intentosReconexion = 0
        void reconectarConResync()
      })
    }

    return (next) => (action) => {
      if (salaActions.conectarWs.match(action)) {
        codigoActual = action.payload
        intentosReconexion = 0
        limpiarTemporizador()
        conexion?.cerrar()
        abrirConexion(action.payload)
      } else if (salaActions.desconectarWs.match(action)) {
        codigoActual = null
        limpiarTemporizador()
        conexion?.cerrar()
        conexion = null
      } else if (salaActions.robarCarta.match(action)) {
        conexion?.enviar({ evento: 'robar_carta', datos: {} })
      } else if (salaActions.enviarPrediccion.match(action)) {
        conexion?.enviar({
          evento: 'prediccion_secreta',
          datos: { prediccion: action.payload },
        })
      } else if (salaActions.enviarVoto.match(action)) {
        conexion?.enviar({ evento: 'voto', datos: { opcion: action.payload } })
      } else if (salaActions.siguienteTurno.match(action)) {
        conexion?.enviar({ evento: 'siguiente_turno', datos: {} })
      }

      return next(action)
    }
  }
}
