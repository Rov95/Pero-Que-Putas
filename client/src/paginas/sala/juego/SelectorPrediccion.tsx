import { useState } from 'react'
import Boton from '../../../componentes/Boton'
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import { salaActions } from '../../../store/slices/salaSlice'
import type { PrediccionClave } from '../../../tipos/modelos'

export default function SelectorPrediccion() {
  const dispatch = useAppDispatch()
  const predicciones = useAppSelector((state) => state.constantes.predicciones)
  const [seleccion, setSeleccion] = useState<PrediccionClave | null>(null)
  const [confirmado, setConfirmado] = useState(false)

  function confirmar() {
    if (!seleccion) return
    dispatch(salaActions.enviarPrediccion(seleccion))
    setConfirmado(true)
  }

  if (confirmado) {
    return <p className="text-center text-white/70">Predicción enviada. Abriendo la votación…</p>
  }

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 p-5">
      <p className="text-center text-white/80">¿Qué crees que votará el grupo?</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {predicciones.map((prediccion) => (
          <button
            key={prediccion.clave}
            type="button"
            onClick={() => setSeleccion(prediccion.clave)}
            className={`min-h-11 rounded-xl border px-4 py-3 text-sm font-medium transition-colors ${
              seleccion === prediccion.clave
                ? 'border-primario-400 bg-primario-500/20 text-white'
                : 'border-white/10 bg-superficie-alta/50 text-white/70 hover:border-primario-400/40'
            }`}
          >
            {prediccion.etiqueta}
          </button>
        ))}
      </div>
      <Boton onClick={confirmar} disabled={!seleccion} className="self-center">
        Confirmar predicción
      </Boton>
    </div>
  )
}
