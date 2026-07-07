import { useState } from 'react'
import { Link } from 'react-router-dom'
import Boton from '../../../componentes/Boton'
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import { salaActions } from '../../../store/slices/salaSlice'
import SelectorPrediccion from './SelectorPrediccion'

export default function PanelLector() {
  const dispatch = useAppDispatch()
  const ronda = useAppSelector((state) => state.sala.ronda)
  const errorJuego = useAppSelector((state) => state.sala.errorJuego)
  const [robando, setRobando] = useState(false)

  function manejarRobar() {
    setRobando(true)
    dispatch(salaActions.robarCarta())
    setTimeout(() => setRobando(false), 1500)
  }

  if (ronda.etapa === null) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-white/10 p-6 text-center">
        <p className="text-white/70">Es tu turno de leer. Roba una carta para empezar la ronda.</p>
        <Boton onClick={manejarRobar} cargando={robando}>
          Robar carta
        </Boton>
        {errorJuego === 'No quedan preguntas disponibles' && (
          <p className="text-sm text-error">
            No quedan cartas.{' '}
            <Link to="/preguntas" className="underline">
              Crea más preguntas
            </Link>{' '}
            o pídele al anfitrión que finalice la partida.
          </p>
        )}
      </div>
    )
  }

  if (ronda.etapa === 'leyendo') {
    return <SelectorPrediccion />
  }

  if (ronda.etapa === 'votando') {
    return (
      <p className="text-center text-white/70">
        Predicción guardada. Esperando los votos del resto…
      </p>
    )
  }

  return null
}
