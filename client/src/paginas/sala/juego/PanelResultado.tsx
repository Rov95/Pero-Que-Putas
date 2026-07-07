import Boton from '../../../componentes/Boton'
import { selectLector, selectSoyAnfitrion, selectSoyLector } from '../../../seleccionadores/juego'
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import { salaActions } from '../../../store/slices/salaSlice'
import type { OpcionVoto, ResultadoClave } from '../../../tipos/modelos'

const etiquetasResultado: Record<ResultadoClave, string> = {
  mayoria_1: 'La mayoría eligió la Opción 1',
  todos_1: '¡Unanimidad! Todos eligieron la Opción 1',
  mayoria_2: 'La mayoría eligió la Opción 2',
  todos_2: '¡Unanimidad! Todos eligieron la Opción 2',
  empate: '¡Empate! Nadie puntúa',
}

export default function PanelResultado() {
  const dispatch = useAppDispatch()
  const resultado = useAppSelector((state) => state.sala.ronda.resultado)
  const predicciones = useAppSelector((state) => state.constantes.predicciones)
  const lector = useAppSelector(selectLector)
  const soyLector = useAppSelector(selectSoyLector)
  const soyAnfitrion = useAppSelector(selectSoyAnfitrion)

  if (!resultado) return null

  const etiquetaPrediccion =
    predicciones.find((p) => p.clave === resultado.prediccion)?.etiqueta ?? resultado.prediccion

  return (
    <div
      aria-live="polite"
      className="animate-revelar flex flex-col gap-4 rounded-2xl border border-acento-500/30 bg-acento-500/5 p-5 text-center"
    >
      <p className="font-display text-xl text-white">{etiquetasResultado[resultado.resultado]}</p>

      <div className="flex flex-col gap-1 text-sm text-white/70">
        {resultado.votos.map((voto) => (
          <p key={voto.usuario_id}>
            {voto.username} votó <VotoEtiqueta opcion={voto.opcion} />
          </p>
        ))}
      </div>

      <p className="text-sm text-white/60">
        Predicción de {lector?.username}: <span className="text-white">{etiquetaPrediccion}</span>
      </p>

      {resultado.acierto ? (
        <p className="text-exito text-lg font-semibold">✅ +1 punto para {lector?.username}</p>
      ) : (
        <p className="text-lg font-semibold text-error">❌ El lector falló su predicción</p>
      )}

      {(soyLector || soyAnfitrion) && (
        <Boton onClick={() => dispatch(salaActions.siguienteTurno())} className="self-center">
          Siguiente turno
        </Boton>
      )}
    </div>
  )
}

function VotoEtiqueta({ opcion }: { opcion: OpcionVoto }) {
  return (
    <span className={opcion === 1 ? 'font-semibold text-opcion-1' : 'font-semibold text-opcion-2'}>
      Opción {opcion}
    </span>
  )
}
