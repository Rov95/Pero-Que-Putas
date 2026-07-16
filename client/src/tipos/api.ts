import type { MarcadorFinalEntrada, PrediccionClave, Sala } from './modelos'

export interface ErrorRespuesta {
  detalle: string
}

export class ErrorApi extends Error {
  readonly detalle: string
  readonly status: number

  constructor(detalle: string, status: number) {
    super(detalle)
    this.name = 'ErrorApi'
    this.detalle = detalle
    this.status = status
  }
}

export interface CrearUsuarioBody {
  username: string
}

export interface AccionSalaBody {
  usuario_id: string
}

export interface FinalizarRespuesta {
  sala: Sala
  marcador_final: MarcadorFinalEntrada[]
}

export interface OpcionesPregunta {
  opcion_1: string
  opcion_2: string
}

/** Cuerpo de POST /api/preguntas y PUT /api/preguntas/{id}. */
export interface CrearPreguntaBody extends OpcionesPregunta {
  enunciado: string
}

export interface ActualizarPuntosBody {
  puntos: number
}

export interface PrediccionConstante {
  clave: PrediccionClave
  etiqueta: string
}

export interface ParametrosPaginacion {
  desplazamiento?: number
  limite?: number
}

/** Extrae el mensaje en español de un ErrorApi; relanza cualquier otro error inesperado. */
export function detalleDeError(error: unknown): string {
  if (error instanceof ErrorApi) return error.detalle
  throw error
}
