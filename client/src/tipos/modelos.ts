export type EstadoSala = 'esperando' | 'en_curso' | 'finalizada'

export type EtapaRonda = 'leyendo' | 'votando' | 'resuelta'

export type PrediccionClave = 'mayoria_1' | 'todos_1' | 'mayoria_2' | 'todos_2'

export type ResultadoClave = PrediccionClave | 'empate'

export type OpcionVoto = 1 | 2

export interface Usuario {
  id: string
  username: string
  creado_en: string
}

export interface Opcion {
  numero: OpcionVoto
  texto: string
}

export interface Pregunta {
  id: string
  creado_en: string
  opciones: Opcion[]
}

export interface Jugador {
  usuario_id: string
  username: string
  orden_turno: number | null
  puntos: number
  conectado: boolean
}

export interface Sala {
  id: string
  codigo: string
  estado: EstadoSala
  anfitrion_id: string
  turno_actual: number
  creado_en: string
  jugadores: Jugador[]
}

export interface PuntoJugador {
  usuario_id: string
  username: string
  puntos: number
}

export interface MarcadorFinalEntrada {
  usuario_id: string
  username: string
  puntos_finales: number
  gano: boolean
}

export interface MarcadorHistoricoEntrada {
  username: string
  puntos_totales: number
  partidas: number
  victorias: number
}
