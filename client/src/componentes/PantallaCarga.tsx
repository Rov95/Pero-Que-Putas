interface Props {
  mensaje?: string
}

export default function PantallaCarga({ mensaje = 'Cargando…' }: Props) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-3 text-white/70">
      <span
        className="size-8 animate-spin rounded-full border-4 border-white/20 border-t-primario-400"
        aria-hidden="true"
      />
      <p role="status">{mensaje}</p>
    </div>
  )
}
