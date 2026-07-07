import { Navigate, useParams } from 'react-router-dom'
import PantallaCarga from '../../componentes/PantallaCarga'
import { useAppSelector } from '../../store/hooks'
import { normalizarCodigoSala } from '../../utilidades/codigoSala'
import { useEnfoqueAlMontar } from '../../utilidades/useEnfoqueAlMontar'
import VistaJuego from './VistaJuego'
import VistaLobby from './VistaLobby'
import VistaPodio from './VistaPodio'
import { useConexionSala } from './useConexionSala'

export default function PaginaSala() {
  const parametros = useParams<{ codigo: string }>()
  const codigo = normalizarCodigoSala(parametros.codigo ?? '')
  const usuario = useAppSelector((state) => state.sesion.usuario)
  const { sala, cargando, conexion } = useAppSelector((state) => state.sala)
  const refContenido = useEnfoqueAlMontar<HTMLDivElement>(sala?.estado)

  useConexionSala(codigo)

  if (!usuario) return <Navigate to="/" replace />

  if (!sala) return <PantallaCarga mensaje={cargando ? 'Entrando a la sala…' : 'Conectando…'} />

  return (
    <div
      ref={refContenido}
      tabIndex={-1}
      className="mx-auto min-h-dvh max-w-2xl px-4 py-6 outline-none"
    >
      {conexion !== 'conectado' && (
        <div
          role="status"
          className="mb-4 rounded-xl border border-acento-500/40 bg-acento-500/10 px-4 py-2 text-center text-sm text-acento-400"
        >
          {conexion === 'reconectando'
            ? 'Reconectando…'
            : conexion === 'conectando'
              ? 'Conectando…'
              : 'Sin conexión'}
        </div>
      )}

      {sala.estado === 'esperando' && <VistaLobby />}
      {sala.estado === 'en_curso' && <VistaJuego />}
      {sala.estado === 'finalizada' && <VistaPodio />}
    </div>
  )
}
