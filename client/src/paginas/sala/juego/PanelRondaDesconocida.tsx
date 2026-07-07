import Boton from '../../../componentes/Boton'
import { selectSoyAnfitrion, selectSoyLector } from '../../../seleccionadores/juego'
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import { salaActions } from '../../../store/slices/salaSlice'

/**
 * El snapshot REST no distingue "todavía no se robó carta este turno" de "hay una ronda
 * activa en una etapa que no conocemos" (limitación del backend). Como no podemos saber
 * cuál es, ofrecemos ambas acciones de recuperación: si fallan por reglas de negocio
 * (ronda ya activa / etapa incorrecta), el backend las rechaza con un toast, sin romper nada.
 */
export default function PanelRondaDesconocida() {
  const dispatch = useAppDispatch()
  const soyLector = useAppSelector(selectSoyLector)
  const soyAnfitrion = useAppSelector(selectSoyAnfitrion)

  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-white/10 p-6 text-center">
      <p className="text-white/70">Hay una ronda en curso… esperando la próxima jugada.</p>

      {soyLector && (
        <Boton onClick={() => dispatch(salaActions.robarCarta())}>Robar carta</Boton>
      )}

      {soyAnfitrion && (
        <Boton variante="secundario" onClick={() => dispatch(salaActions.siguienteTurno())}>
          Forzar siguiente turno
        </Boton>
      )}
    </div>
  )
}
