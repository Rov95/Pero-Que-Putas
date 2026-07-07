import { Link, useNavigate } from 'react-router-dom'
import Boton from '../../componentes/Boton'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { puntajesActions } from '../../store/slices/puntajesSlice'
import { salaActions } from '../../store/slices/salaSlice'
import { almacenamiento } from '../../utilidades/almacenamiento'

export default function VistaPodio() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const marcadorFinal = useAppSelector((state) => state.puntajes.marcadorFinal)

  function volverAlInicio() {
    dispatch(salaActions.limpiarSala())
    dispatch(puntajesActions.limpiarMarcadorFinal())
    almacenamiento.eliminarSalaCodigo()
    navigate('/')
  }

  if (!marcadorFinal) {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <p className="text-lg text-white/80">Esta partida ya terminó.</p>
        <div className="flex gap-3">
          <Boton onClick={volverAlInicio}>Volver al inicio</Boton>
          <Link to="/marcador" className="flex items-center text-primario-300 hover:underline">
            Ver marcador histórico
          </Link>
        </div>
      </div>
    )
  }

  const ganadores = marcadorFinal.filter((entrada) => entrada.gano)
  const resto = marcadorFinal
    .filter((entrada) => !entrada.gano)
    .sort((a, b) => b.puntos_finales - a.puntos_finales)

  return (
    <div className="flex flex-col items-center gap-8 py-10 text-center">
      <div>
        <p className="text-sm tracking-widest text-acento-400 uppercase">
          {ganadores.length > 1 ? '¡Ganadores!' : '¡Ganador!'}
        </p>
        <div className="mt-2 flex flex-col gap-1">
          {ganadores.map((ganador) => (
            <p key={ganador.usuario_id} className="font-display text-3xl font-bold text-white">
              🏆 {ganador.username} — {ganador.puntos_finales} pts
            </p>
          ))}
        </div>
      </div>

      {resto.length > 0 && (
        <div className="flex flex-col gap-1">
          {resto.map((entrada, indice) => (
            <p key={entrada.usuario_id} className="text-white/70">
              {indice + 2}. {entrada.username} — {entrada.puntos_finales} pts
            </p>
          ))}
        </div>
      )}

      <p className="text-sm text-white/40">Para jugar otra vez, crea una sala nueva.</p>

      <div className="flex gap-3">
        <Boton onClick={volverAlInicio}>Volver al inicio</Boton>
        <Link to="/marcador" className="flex items-center text-primario-300 hover:underline">
          Ver marcador histórico
        </Link>
      </div>
    </div>
  )
}
