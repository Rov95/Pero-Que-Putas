import { useState, type FormEvent } from 'react'
import Boton from '../../componentes/Boton'
import type { OpcionesPregunta } from '../../tipos/api'

interface Props {
  valorInicial?: OpcionesPregunta
  textoBoton: string
  onEnviar: (valores: OpcionesPregunta) => Promise<void>
  onCancelar?: () => void
}

export default function FormularioPregunta({
  valorInicial,
  textoBoton,
  onEnviar,
  onCancelar,
}: Props) {
  const [opcion1, setOpcion1] = useState(valorInicial?.opcion_1 ?? '')
  const [opcion2, setOpcion2] = useState(valorInicial?.opcion_2 ?? '')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault()
    if (!opcion1.trim() || !opcion2.trim()) {
      setError('Ambas opciones son obligatorias')
      return
    }
    setError(null)
    setEnviando(true)
    try {
      await onEnviar({ opcion_1: opcion1.trim(), opcion_2: opcion2.trim() })
      if (!valorInicial) {
        setOpcion1('')
        setOpcion2('')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error de conexión con el servidor')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form
      onSubmit={manejarEnvio}
      className="flex flex-col gap-3 rounded-2xl border border-white/10 p-4"
    >
      <label className="flex flex-col gap-1.5 text-sm font-medium text-white/80">
        Opción 1
        <textarea
          value={opcion1}
          onChange={(evento) => setOpcion1(evento.target.value)}
          placeholder="p. ej. Ir a la playa"
          rows={2}
          className="rounded-xl border border-white/10 bg-superficie px-4 py-2.5 text-white placeholder:text-white/30 focus:border-opcion-1/60 focus:ring-2 focus:ring-opcion-1/30 focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-medium text-white/80">
        Opción 2
        <textarea
          value={opcion2}
          onChange={(evento) => setOpcion2(evento.target.value)}
          placeholder="p. ej. Ir a la montaña"
          rows={2}
          className="rounded-xl border border-white/10 bg-superficie px-4 py-2.5 text-white placeholder:text-white/30 focus:border-opcion-2/60 focus:ring-2 focus:ring-opcion-2/30 focus:outline-none"
        />
      </label>
      {error && <p className="text-sm text-error">{error}</p>}
      <div className="flex gap-2">
        <Boton type="submit" cargando={enviando}>
          {textoBoton}
        </Boton>
        {onCancelar && (
          <Boton type="button" variante="fantasma" onClick={onCancelar}>
            Cancelar
          </Boton>
        )}
      </div>
    </form>
  )
}
