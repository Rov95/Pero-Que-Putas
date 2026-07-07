import { useEffect } from 'react'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { uiActions, type TipoNotificacion } from '../store/slices/uiSlice'

const estilosPorTipo: Record<TipoNotificacion, string> = {
  error: 'border-error/50 bg-error/10 text-error',
  exito: 'border-exito/50 bg-exito/10 text-exito',
  info: 'border-primario-400/50 bg-primario-500/10 text-primario-200',
}

export default function Notificaciones() {
  const notificaciones = useAppSelector((state) => state.ui.notificaciones)

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4"
    >
      {notificaciones.map((n) => (
        <ToastItem key={n.id} id={n.id} tipo={n.tipo} mensaje={n.mensaje} />
      ))}
    </div>
  )
}

function ToastItem({
  id,
  tipo,
  mensaje,
}: {
  id: string
  tipo: TipoNotificacion
  mensaje: string
}) {
  const dispatch = useAppDispatch()

  useEffect(() => {
    const temporizador = setTimeout(() => dispatch(uiActions.descartar(id)), 5000)
    return () => clearTimeout(temporizador)
  }, [id, dispatch])

  return (
    <div
      role="status"
      className={`pointer-events-auto w-full max-w-sm rounded-xl border px-4 py-3 shadow-lg backdrop-blur ${estilosPorTipo[tipo]}`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm">{mensaje}</p>
        <button
          type="button"
          onClick={() => dispatch(uiActions.descartar(id))}
          aria-label="Descartar notificación"
          className="text-white/50 hover:text-white"
        >
          ✕
        </button>
      </div>
    </div>
  )
}
