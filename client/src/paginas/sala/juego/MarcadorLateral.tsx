import { selectJugadoresOrdenadosPorPuntos, selectLector } from '../../../seleccionadores/juego'
import { useAppSelector } from '../../../store/hooks'

export default function MarcadorLateral() {
  const jugadores = useAppSelector(selectJugadoresOrdenadosPorPuntos)
  const lector = useAppSelector(selectLector)
  const miId = useAppSelector((state) => state.sesion.usuario?.id)

  return (
    <aside className="fixed inset-x-0 bottom-0 z-30 border-t border-white/10 bg-superficie/95 p-4 backdrop-blur md:static md:w-56 md:rounded-2xl md:border md:border-white/10 md:bg-superficie-alta/40">
      <p className="mb-2 text-xs tracking-wide text-white/40 uppercase">Marcador</p>
      <ul className="flex gap-3 overflow-x-auto md:flex-col md:gap-2">
        {jugadores.map((jugador, indice) => (
          <li
            key={jugador.usuario_id}
            className={`flex shrink-0 items-center justify-between gap-3 rounded-lg px-2 py-1 text-sm md:w-full ${
              jugador.usuario_id === lector?.usuario_id ? 'bg-primario-500/15' : ''
            }`}
          >
            <span className="text-white/80">
              {indice + 1}. {jugador.username}
              {jugador.usuario_id === miId && ' (tú)'}
            </span>
            <span className="font-display font-semibold text-white">{jugador.puntos}</span>
          </li>
        ))}
      </ul>
    </aside>
  )
}
