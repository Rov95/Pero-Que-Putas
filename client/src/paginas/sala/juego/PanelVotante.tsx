import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import { salaActions } from '../../../store/slices/salaSlice'

export default function PanelVotante() {
  const dispatch = useAppDispatch()
  const ronda = useAppSelector((state) => state.sala.ronda)

  if (ronda.etapa === null || ronda.etapa === 'leyendo') {
    return <p className="text-center text-white/60">El lector está leyendo la carta…</p>
  }

  if (ronda.miVoto) {
    return <p className="text-exito text-center">Voto registrado ✓ Esperando al resto…</p>
  }

  return (
    <div className="flex justify-center gap-4">
      <button
        type="button"
        onClick={() => dispatch(salaActions.enviarVoto(1))}
        className="min-h-16 max-w-40 flex-1 rounded-2xl border-2 border-opcion-1/50 bg-opcion-1/10 text-3xl font-bold text-opcion-1 transition-transform active:scale-95"
        aria-label="Votar Opción 1"
      >
        1 ☝️
      </button>
      <button
        type="button"
        onClick={() => dispatch(salaActions.enviarVoto(2))}
        className="min-h-16 max-w-40 flex-1 rounded-2xl border-2 border-opcion-2/50 bg-opcion-2/10 text-3xl font-bold text-opcion-2 transition-transform active:scale-95"
        aria-label="Votar Opción 2"
      >
        2 ✌️
      </button>
    </div>
  )
}
