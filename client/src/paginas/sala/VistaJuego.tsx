import { useEffect, useState } from 'react'
import Boton from '../../componentes/Boton'
import TarjetaDilema from '../../componentes/TarjetaDilema'
import { selectLector, selectSoyAnfitrion, selectSoyLector } from '../../seleccionadores/juego'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { cargarPredicciones } from '../../store/slices/constantesSlice'
import { finalizarPartida } from '../../store/slices/salaSlice'
import { uiActions } from '../../store/slices/uiSlice'
import MarcadorLateral from './juego/MarcadorLateral'
import PanelLector from './juego/PanelLector'
import PanelResultado from './juego/PanelResultado'
import PanelRondaDesconocida from './juego/PanelRondaDesconocida'
import PanelVotante from './juego/PanelVotante'
import ProgresoVotos from './juego/ProgresoVotos'

export default function VistaJuego() {
  const dispatch = useAppDispatch()
  const ronda = useAppSelector((state) => state.sala.ronda)
  const lector = useAppSelector(selectLector)
  const soyLector = useAppSelector(selectSoyLector)
  const soyAnfitrion = useAppSelector(selectSoyAnfitrion)
  const cargadoConstantes = useAppSelector((state) => state.constantes.cargado)
  const cargando = useAppSelector((state) => state.sala.cargando)
  const [confirmandoFinalizar, setConfirmandoFinalizar] = useState(false)

  useEffect(() => {
    if (!cargadoConstantes) dispatch(cargarPredicciones())
  }, [cargadoConstantes, dispatch])

  async function manejarFinalizar() {
    const resultado = await dispatch(finalizarPartida())
    if (finalizarPartida.rejected.match(resultado)) {
      dispatch(uiActions.notificar(resultado.payload ?? 'No se pudo finalizar la partida', 'error'))
    }
    setConfirmandoFinalizar(false)
  }

  return (
    <div className="flex flex-col gap-6 pb-28 md:flex-row md:pb-0">
      <div className="flex flex-1 flex-col gap-6">
        <header className="flex items-center justify-between gap-3">
          <div key={lector?.usuario_id} className="animate-aparecer">
            <p className="text-sm text-white/50">
              Turno de <span className="font-semibold text-white">{lector?.username}</span>
              {soyLector && ' (tú)'}
            </p>
            {lector && !lector.conectado && (
              <p className="text-sm text-error">El lector está desconectado</p>
            )}
          </div>
          {soyAnfitrion && !confirmandoFinalizar && (
            <Boton variante="peligro" onClick={() => setConfirmandoFinalizar(true)}>
              Finalizar partida
            </Boton>
          )}
        </header>

        {confirmandoFinalizar && (
          <div className="animate-aparecer rounded-xl border border-error/40 bg-error/10 p-4 text-center">
            <p className="mb-3 text-white">¿Terminar la partida para todos?</p>
            <div className="flex justify-center gap-3">
              <Boton variante="peligro" onClick={manejarFinalizar} cargando={cargando}>
                Sí, terminar
              </Boton>
              <Boton variante="fantasma" onClick={() => setConfirmandoFinalizar(false)}>
                Cancelar
              </Boton>
            </div>
          </div>
        )}

        {ronda.desconocida && <PanelRondaDesconocida />}

        {!ronda.desconocida && ronda.pregunta && (
          <div key={ronda.id} className="animate-aparecer">
            <TarjetaDilema
              enunciado={ronda.pregunta.enunciado}
              opcion1={ronda.pregunta.opcion_1}
              opcion2={ronda.pregunta.opcion_2}
            />
          </div>
        )}

        {!ronda.desconocida && ronda.etapa === 'votando' && <ProgresoVotos />}

        {!ronda.desconocida && soyLector && <PanelLector />}
        {!ronda.desconocida && !soyLector && ronda.etapa !== 'resuelta' && <PanelVotante />}
        {!ronda.desconocida && ronda.etapa === 'resuelta' && <PanelResultado />}
      </div>

      <MarcadorLateral />
    </div>
  )
}
