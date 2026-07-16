import type { MarcadorFinalEntrada, OpcionVoto, PrediccionClave, ResultadoClave } from './modelos'

export interface SobreWs<E extends string, D> {
  evento: E
  datos: D
}

/** Forma de la pregunta dentro de una ronda: distinta al modelo REST `Pregunta` (sin array `opciones`). */
export interface PreguntaEnRonda {
  id: string
  enunciado: string
  opcion_1: string
  opcion_2: string
}

export interface ResumenJugador {
  usuario_id: string
  username: string
}

// ---- Cliente -> Servidor ----

export type EventoRobarCarta = SobreWs<'robar_carta', Record<string, never>>
export type EventoPrediccionSecreta = SobreWs<
  'prediccion_secreta',
  { prediccion: PrediccionClave }
>
export type EventoVoto = SobreWs<'voto', { opcion: OpcionVoto }>
export type EventoSiguienteTurno = SobreWs<'siguiente_turno', Record<string, never>>

export type EventoCliente =
  | EventoRobarCarta
  | EventoPrediccionSecreta
  | EventoVoto
  | EventoSiguienteTurno

// ---- Servidor -> Cliente ----

export type EventoJugadorUnido = SobreWs<'jugador_unido', ResumenJugador>
export type EventoJugadorSalio = SobreWs<'jugador_salio', ResumenJugador>
export type EventoPartidaIniciada = SobreWs<
  'partida_iniciada',
  {
    orden: Array<ResumenJugador & { orden_turno: number }>
    lector: ResumenJugador
  }
>
export type EventoTurnoActual = SobreWs<
  'turno_actual',
  { numero: number; lector: ResumenJugador }
>
export type EventoCartaRobada = SobreWs<
  'carta_robada',
  { ronda_id: string; pregunta: PreguntaEnRonda }
>
export type EventoPrediccionRegistrada = SobreWs<
  'prediccion_registrada',
  { lector_id: string }
>
export type EventoVotoRegistrado = SobreWs<
  'voto_registrado',
  { votos_recibidos: number; votos_esperados: number }
>
export type EventoResultadoRonda = SobreWs<
  'resultado_ronda',
  {
    votos: Array<ResumenJugador & { opcion: OpcionVoto }>
    resultado: ResultadoClave
    prediccion: PrediccionClave
    acierto: boolean
    puntos_lector: number
  }
>
export type EventoPartidaFinalizada = SobreWs<
  'partida_finalizada',
  { marcador_final: MarcadorFinalEntrada[] }
>
export type EventoErrorWs = SobreWs<'error', { detalle: string }>

export type EventoServidor =
  | EventoJugadorUnido
  | EventoJugadorSalio
  | EventoPartidaIniciada
  | EventoTurnoActual
  | EventoCartaRobada
  | EventoPrediccionRegistrada
  | EventoVotoRegistrado
  | EventoResultadoRonda
  | EventoPartidaFinalizada
  | EventoErrorWs

export type DatosResultadoRonda = EventoResultadoRonda['datos']
