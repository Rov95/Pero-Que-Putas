import { useAppSelector } from '../../../store/hooks'

export default function ProgresoVotos() {
  const { votosRecibidos, votosEsperados } = useAppSelector((state) => state.sala.ronda)
  const porcentaje = votosEsperados > 0 ? (votosRecibidos / votosEsperados) * 100 : 0

  return (
    <div aria-live="polite" className="flex flex-col gap-1">
      <p className="text-center text-sm text-white/60">
        Votos: {votosRecibidos}/{votosEsperados}
      </p>
      <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-primario-500 transition-all"
          style={{ width: `${porcentaje}%` }}
        />
      </div>
    </div>
  )
}
