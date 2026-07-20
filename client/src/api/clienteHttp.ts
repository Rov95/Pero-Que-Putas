import { ErrorApi, type ErrorRespuesta } from '../tipos/api'
import { almacenamiento } from '../utilidades/almacenamiento'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function urlWsSala(codigo: string, token: string): string {
  const wsBase = BASE_URL.replace(/^http/, 'ws')
  return `${wsBase}/ws/salas/${codigo}?token=${encodeURIComponent(token)}`
}

// Invocado ante cualquier respuesta 401 (sesión revocada/expirada) antes de lanzar
// el error; el store lo registra para limpiar la sesión local automáticamente.
let manejador401: (() => void) | null = null

export function establecerManejador401(manejador: () => void): void {
  manejador401 = manejador
}

interface OpcionesPeticion {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  params?: Record<string, string | number | undefined>
}

function construirUrl(ruta: string, params?: OpcionesPeticion['params']): string {
  const url = new URL(`${BASE_URL}${ruta}`)
  if (params) {
    for (const [clave, valor] of Object.entries(params)) {
      if (valor !== undefined) url.searchParams.set(clave, String(valor))
    }
  }
  return url.toString()
}

function construirCabeceras(body: unknown): Record<string, string> | undefined {
  const cabeceras: Record<string, string> = {}
  if (body !== undefined) cabeceras['Content-Type'] = 'application/json'
  const token = almacenamiento.obtenerToken()
  if (token) cabeceras['Authorization'] = `Bearer ${token}`
  return Object.keys(cabeceras).length > 0 ? cabeceras : undefined
}

async function peticion<T>(ruta: string, opciones: OpcionesPeticion = {}): Promise<T> {
  const { method = 'GET', body, params } = opciones

  let respuesta: Response
  try {
    respuesta = await fetch(construirUrl(ruta, params), {
      method,
      headers: construirCabeceras(body),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ErrorApi('Error de conexión con el servidor', 0)
  }

  if (!respuesta.ok) {
    let detalle = 'Error de conexión con el servidor'
    try {
      const cuerpo = (await respuesta.json()) as ErrorRespuesta
      if (cuerpo?.detalle) detalle = cuerpo.detalle
    } catch {
      // sin body JSON: se mantiene el mensaje por defecto
    }
    if (respuesta.status === 401) manejador401?.()
    throw new ErrorApi(detalle, respuesta.status)
  }

  if (respuesta.status === 204) {
    return undefined as T
  }

  return (await respuesta.json()) as T
}

export const clienteHttp = {
  get: <T>(ruta: string, params?: OpcionesPeticion['params']) =>
    peticion<T>(ruta, { method: 'GET', params }),
  post: <T>(ruta: string, body?: unknown) => peticion<T>(ruta, { method: 'POST', body }),
  put: <T>(ruta: string, body?: unknown) => peticion<T>(ruta, { method: 'PUT', body }),
  delete: <T>(ruta: string) => peticion<T>(ruta, { method: 'DELETE' }),
}
