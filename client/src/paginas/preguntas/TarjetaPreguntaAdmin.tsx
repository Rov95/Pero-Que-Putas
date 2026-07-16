import { useState } from 'react'
import Boton from '../../componentes/Boton'
import type { CrearPreguntaBody } from '../../tipos/api'
import type { Pregunta } from '../../tipos/modelos'
import FormularioPregunta from './FormularioPregunta'

interface Props {
  pregunta: Pregunta
  onActualizar: (id: string, valores: CrearPreguntaBody) => Promise<void>
  onEliminar: (id: string) => Promise<void>
}

export default function TarjetaPreguntaAdmin({ pregunta, onActualizar, onEliminar }: Props) {
  const [editando, setEditando] = useState(false)
  const [confirmandoEliminar, setConfirmandoEliminar] = useState(false)
  const opcion1 = pregunta.opciones.find((o) => o.numero === 1)?.texto ?? ''
  const opcion2 = pregunta.opciones.find((o) => o.numero === 2)?.texto ?? ''

  if (editando) {
    return (
      <FormularioPregunta
        valorInicial={{ enunciado: pregunta.enunciado, opcion_1: opcion1, opcion_2: opcion2 }}
        textoBoton="Guardar cambios"
        onCancelar={() => setEditando(false)}
        onEnviar={async (valores) => {
          await onActualizar(pregunta.id, valores)
          setEditando(false)
        }}
      />
    )
  }

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-white/10 p-4">
      <p className="text-sm font-medium text-white">{pregunta.enunciado}</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <p className="rounded-lg bg-opcion-1/10 px-3 py-2 text-sm text-white">{opcion1}</p>
        <p className="rounded-lg bg-opcion-2/10 px-3 py-2 text-sm text-white">{opcion2}</p>
      </div>
      {confirmandoEliminar ? (
        <div className="flex items-center justify-between gap-2 rounded-lg bg-error/10 px-3 py-2">
          <p className="text-sm text-error">¿Eliminar esta pregunta?</p>
          <div className="flex gap-2">
            <Boton variante="peligro" onClick={() => onEliminar(pregunta.id)}>
              Eliminar
            </Boton>
            <Boton variante="fantasma" onClick={() => setConfirmandoEliminar(false)}>
              Cancelar
            </Boton>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          <Boton variante="secundario" onClick={() => setEditando(true)}>
            Editar
          </Boton>
          <Boton variante="peligro" onClick={() => setConfirmandoEliminar(true)}>
            Eliminar
          </Boton>
        </div>
      )}
    </div>
  )
}
