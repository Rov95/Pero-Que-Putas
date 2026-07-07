import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variante = 'primario' | 'secundario' | 'peligro' | 'fantasma'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante
  cargando?: boolean
  children: ReactNode
}

const clasesPorVariante: Record<Variante, string> = {
  primario: 'bg-primario-600 text-white hover:bg-primario-500 active:bg-primario-700',
  secundario:
    'bg-superficie-alta text-white border border-primario-800 hover:bg-primario-950',
  peligro: 'bg-error/90 text-white hover:bg-error',
  fantasma: 'bg-transparent text-primario-200 hover:bg-superficie-alta',
}

export default function Boton({
  variante = 'primario',
  cargando = false,
  disabled,
  children,
  className = '',
  ...resto
}: Props) {
  return (
    <button
      type="button"
      disabled={disabled || cargando}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 py-2.5 font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${clasesPorVariante[variante]} ${className}`}
      {...resto}
    >
      {cargando && (
        <span
          className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
          aria-hidden="true"
        />
      )}
      {children}
    </button>
  )
}
