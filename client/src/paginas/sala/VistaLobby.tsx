import { useState } from 'react'
import Boton from '../../componentes/Boton'
import FichaJugador from '../../componentes/FichaJugador'
import { selectSoyAnfitrion } from '../../seleccionadores/juego'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { iniciarPartida } from '../../store/slices/salaSlice'
import { uiActions } from '../../store/slices/uiSlice'

export default function VistaLobby() {
  const dispatch = useAppDispatch()
  // PaginaSala solo renderiza esta vista cuando `sala` ya existe.
  const sala = useAppSelector((state) => state.sala.sala)!
  const soyAnfitrion = useAppSelector(selectSoyAnfitrion)
  const miId = useAppSelector((state) => state.sesion.usuario?.id)
  const cargando = useAppSelector((state) => state.sala.cargando)
  const [copiado, setCopiado] = useState(false)

  const conectados = sala.jugadores.filter((j) => j.conectado).length
  const anfitrion = sala.jugadores.find((j) => j.usuario_id === sala.anfitrion_id)

  async function copiarCodigo() {
    try {
      await navigator.clipboard.writeText(sala.codigo)
      setCopiado(true)
      dispatch(uiActions.notificar('Código copiado', 'exito'))
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      dispatch(uiActions.notificar('No se pudo copiar el código', 'error'))
    }
  }

  async function manejarIniciar() {
    const resultado = await dispatch(iniciarPartida())
    if (iniciarPartida.rejected.match(resultado)) {
      dispatch(uiActions.notificar(resultado.payload ?? 'No se pudo iniciar la partida', 'error'))
    }
  }

  return (
    <div className="flex flex-col items-center gap-8 py-8">
      <div className="text-center">
        <p className="text-sm tracking-widest text-white/50 uppercase">Código de la sala</p>
        <p className="font-display text-5xl font-bold tracking-[0.2em] text-white">
          {sala.codigo}
        </p>
        <button
          type="button"
          onClick={copiarCodigo}
          className="mt-2 text-sm text-primario-300 underline-offset-4 hover:underline"
        >
          {copiado ? 'Copiado ✓' : 'Copiar código'}
        </button>
      </div>

      <div className="w-full max-w-sm">
        <p className="mb-2 text-sm text-white/50">Jugadores ({conectados} conectados)</p>
        <div className="flex flex-col gap-2">
          {sala.jugadores.map((jugador) => (
            <FichaJugador
              key={jugador.usuario_id}
              jugador={jugador}
              esAnfitrion={jugador.usuario_id === sala.anfitrion_id}
              soyYo={jugador.usuario_id === miId}
            />
          ))}
        </div>
      </div>

      {soyAnfitrion ? (
        <div className="flex flex-col items-center gap-2">
          <Boton onClick={manejarIniciar} disabled={conectados < 2} cargando={cargando}>
            Iniciar partida
          </Boton>
          {conectados < 2 && (
            <p className="text-sm text-white/50">Se necesitan al menos 2 jugadores</p>
          )}
        </div>
      ) : (
        <p className="text-white/60">
          Esperando a que {anfitrion?.username ?? 'el anfitrión'} inicie la partida…
        </p>
      )}
    </div>
  )
}
