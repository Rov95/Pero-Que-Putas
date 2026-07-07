import { useEffect, useRef } from 'react'

/** Mueve el foco a un contenedor cuando cambia `dependencia` (p. ej. al navegar o cambiar de vista). */
export function useEnfoqueAlMontar<T extends HTMLElement>(dependencia?: unknown) {
  const ref = useRef<T>(null)

  useEffect(() => {
    ref.current?.focus()
  }, [dependencia])

  return ref
}
