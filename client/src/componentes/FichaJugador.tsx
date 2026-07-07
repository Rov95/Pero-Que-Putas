import type { Jugador } from '../tipos/modelos'

interface Props {
  jugador: Jugador
  esAnfitrion?: boolean
  esLector?: boolean
  soyYo?: boolean
}

export default function FichaJugador({ jugador, esAnfitrion, esLector, soyYo }: Props) {
  return (
    <div
      className={`flex items-center justify-between rounded-xl px-3 py-2 ${
        esLector ? 'bg-primario-500/15 ring-1 ring-primario-400/40' : 'bg-superficie-alta/50'
      }`}
    >
      <div className="flex min-w-0 items-center gap-2">
        <span
          className={`size-2.5 shrink-0 rounded-full ${jugador.conectado ? 'bg-exito' : 'bg-white/25'}`}
          aria-hidden="true"
        />
        <span className="truncate font-medium text-white">
          {jugador.username}
          {soyYo && <span className="text-white/50"> (tú)</span>}
        </span>
        {esAnfitrion && (
          <span title="Anfitrión" aria-label="Anfitrión">
            👑
          </span>
        )}
        {esLector && (
          <span className="rounded-full bg-primario-500/20 px-2 py-0.5 text-xs text-primario-200">
            Lector
          </span>
        )}
      </div>
      <span className="shrink-0 font-display text-sm text-white/80">{jugador.puntos} pts</span>
    </div>
  )
}
