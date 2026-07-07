import type { InputHTMLAttributes } from 'react'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  etiqueta: string
  error?: string | null
}

export default function CampoTexto({ etiqueta, error, id, className = '', ...resto }: Props) {
  const inputId = id ?? `campo-${etiqueta.toLowerCase().replace(/\s+/g, '-')}`
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-sm font-medium text-white/80">
        {etiqueta}
      </label>
      <input
        id={inputId}
        className={`min-h-11 rounded-xl border border-white/10 bg-superficie px-4 py-2.5 text-white placeholder:text-white/30 focus:border-primario-400 focus:outline-none focus:ring-2 focus:ring-primario-500/40 ${className}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${inputId}-error` : undefined}
        {...resto}
      />
      {error && (
        <p id={`${inputId}-error`} role="alert" className="text-sm text-error">
          {error}
        </p>
      )}
    </div>
  )
}
