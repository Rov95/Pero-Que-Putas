import type { ReactNode } from 'react'

interface Props {
  titulo: string
  descripcion?: string
  accion?: ReactNode
}

export default function EstadoVacio({ titulo, descripcion, accion }: Props) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-white/15 p-8 text-center">
      <p className="font-display text-lg text-white">{titulo}</p>
      {descripcion && <p className="text-sm text-white/60">{descripcion}</p>}
      {accion}
    </div>
  )
}
