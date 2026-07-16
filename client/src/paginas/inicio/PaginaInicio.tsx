import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { salasApi } from '../../api/salasApi'
import { useAppSelector } from '../../store/hooks'
import { almacenamiento } from '../../utilidades/almacenamiento'
import { useEnfoqueAlMontar } from '../../utilidades/useEnfoqueAlMontar'
import BotonCrearSala from './BotonCrearSala'
import BotonPractica from './BotonPractica'
import FormularioRegistro from './FormularioRegistro'
import FormularioUnirse from './FormularioUnirse'

export default function PaginaInicio() {
  const usuario = useAppSelector((state) => state.sesion.usuario)
  const [salaGuardada, setSalaGuardada] = useState<string | null>(null)
  const refContenido = useEnfoqueAlMontar<HTMLDivElement>()

  useEffect(() => {
    if (!usuario) return
    const codigo = almacenamiento.obtenerSalaCodigo()
    if (!codigo) return

    let cancelado = false
    salasApi
      .obtener(codigo)
      .then((sala) => {
        if (!cancelado && sala.estado !== 'finalizada') setSalaGuardada(codigo)
      })
      .catch(() => {
        almacenamiento.eliminarSalaCodigo()
      })
    return () => {
      cancelado = true
    }
  }, [usuario])

  return (
    <div
      ref={refContenido}
      tabIndex={-1}
      className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-8 px-4 py-10 outline-none"
    >
      <header className="text-center">
        <h1 className="font-display text-3xl font-bold text-white">Pero Qué Putas</h1>
        <p className="mt-1 text-white/60">El juego de fiesta de las preferencias imposibles</p>
      </header>

      {!usuario ? (
        <FormularioRegistro />
      ) : (
        <div className="flex w-full flex-col items-center gap-6">
          <p className="text-white/80">
            Hola, <span className="font-semibold text-white">{usuario.username}</span>
          </p>

          {salaGuardada && (
            <Link
              to={`/sala/${salaGuardada}`}
              className="rounded-xl border border-primario-400/40 bg-primario-500/10 px-4 py-2 text-sm text-primario-200 hover:bg-primario-500/20"
            >
              Volver a la sala {salaGuardada}
            </Link>
          )}

          <BotonCrearSala />
          <BotonPractica />

          <div className="flex w-full items-center gap-3 text-white/30">
            <span className="h-px flex-1 bg-white/10" />
            <span className="text-xs uppercase">o</span>
            <span className="h-px flex-1 bg-white/10" />
          </div>

          <FormularioUnirse />

          <nav className="flex gap-4 text-sm text-white/50">
            <Link to="/marcador" className="hover:text-white">
              Marcador histórico
            </Link>
            <Link to="/preguntas" className="hover:text-white">
              Administrar preguntas
            </Link>
          </nav>
        </div>
      )}
    </div>
  )
}
