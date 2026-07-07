import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import EstadoVacio from '../../componentes/EstadoVacio'
import PantallaCarga from '../../componentes/PantallaCarga'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { cargarMarcadorHistorico } from '../../store/slices/puntajesSlice'
import { useEnfoqueAlMontar } from '../../utilidades/useEnfoqueAlMontar'

export default function PaginaMarcador() {
  const dispatch = useAppDispatch()
  const { historico, cargandoHistorico } = useAppSelector((state) => state.puntajes)
  const miUsername = useAppSelector((state) => state.sesion.usuario?.username)
  const refContenido = useEnfoqueAlMontar<HTMLDivElement>()

  useEffect(() => {
    dispatch(cargarMarcadorHistorico())
  }, [dispatch])

  return (
    <div ref={refContenido} tabIndex={-1} className="mx-auto min-h-dvh max-w-2xl px-4 py-8 outline-none">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-white">Marcador histórico</h1>
        <Link to="/" className="text-sm text-primario-300 hover:underline">
          Volver al inicio
        </Link>
      </header>

      {cargandoHistorico && <PantallaCarga mensaje="Cargando marcador…" />}

      {!cargandoHistorico && historico.length === 0 && (
        <EstadoVacio titulo="Todavía no hay partidas terminadas" />
      )}

      {!cargandoHistorico && historico.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-white/50">
                <th className="py-2 pr-4">#</th>
                <th className="py-2 pr-4">Jugador</th>
                <th className="py-2 pr-4">Puntos</th>
                <th className="py-2 pr-4">Partidas</th>
                <th className="py-2">Victorias</th>
              </tr>
            </thead>
            <tbody>
              {historico.map((entrada, indice) => (
                <tr
                  key={entrada.username}
                  className={`border-b border-white/5 ${
                    entrada.username === miUsername ? 'bg-primario-500/10' : ''
                  }`}
                >
                  <td className="py-2 pr-4 text-white/50">{indice + 1}</td>
                  <td className="py-2 pr-4 font-medium text-white">{entrada.username}</td>
                  <td className="py-2 pr-4 text-white">{entrada.puntos_totales}</td>
                  <td className="py-2 pr-4 text-white/70">{entrada.partidas}</td>
                  <td className="py-2 text-white/70">{entrada.victorias}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
