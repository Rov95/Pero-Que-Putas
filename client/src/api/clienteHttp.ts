import { ErrorApi, type ErrorRespuesta } from '../tipos/api'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function urlWsSala(codigo: string, usuarioId: string): string {
  const wsBase = BASE_URL.replace(/^http/, 'ws')
  return `${wsBase}/ws/salas/${codigo}?usuario_id=${encodeURIComponent(usuarioId)}`
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

async function peticion<T>(ruta: string, opciones: OpcionesPeticion = {}): Promise<T> {
  const { method = 'GET', body, params } = opciones

  let respuesta: Response
  try {
    respuesta = await fetch(construirUrl(ruta, params), {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
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
