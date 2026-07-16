import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { preguntasApi } from '../../api/preguntasApi'
import Boton from '../../componentes/Boton'
import EstadoVacio from '../../componentes/EstadoVacio'
import PantallaCarga from '../../componentes/PantallaCarga'
import { ErrorApi, type CrearPreguntaBody } from '../../tipos/api'
import type { Pregunta } from '../../tipos/modelos'
import { useEnfoqueAlMontar } from '../../utilidades/useEnfoqueAlMontar'
import FormularioPregunta from './FormularioPregunta'
import TarjetaPreguntaAdmin from './TarjetaPreguntaAdmin'

const LIMITE_POR_PAGINA = 20

export default function PaginaPreguntas() {
  const [preguntas, setPreguntas] = useState<Pregunta[]>([])
  const [cargando, setCargando] = useState(true)
  const [cargandoMas, setCargandoMas] = useState(false)
  const [hayMas, setHayMas] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const refContenido = useEnfoqueAlMontar<HTMLDivElement>()

  useEffect(() => {
    void cargarPagina(0)
  }, [])

  async function cargarPagina(desplazamiento: number) {
    if (desplazamiento === 0) setCargando(true)
    else setCargandoMas(true)
    try {
      const pagina = await preguntasApi.listar({ desplazamiento, limite: LIMITE_POR_PAGINA })
      setPreguntas((previas) => (desplazamiento === 0 ? pagina : [...previas, ...pagina]))
      setHayMas(pagina.length === LIMITE_POR_PAGINA)
    } catch (e) {
      setError(e instanceof ErrorApi ? e.detalle : 'Error de conexión con el servidor')
    } finally {
      setCargando(false)
      setCargandoMas(false)
    }
  }

  async function crear(valores: CrearPreguntaBody) {
    const nueva = await preguntasApi.crear(valores)
    setPreguntas((previas) => [nueva, ...previas])
  }

  async function actualizar(id: string, valores: CrearPreguntaBody) {
    const actualizada = await preguntasApi.actualizar(id, valores)
    setPreguntas((previas) =>
      previas.map((pregunta) => (pregunta.id === id ? actualizada : pregunta)),
    )
  }

  async function eliminar(id: string) {
    await preguntasApi.eliminar(id)
    setPreguntas((previas) => previas.filter((pregunta) => pregunta.id !== id))
  }

  return (
    <div ref={refContenido} tabIndex={-1} className="mx-auto min-h-dvh max-w-2xl px-4 py-8 outline-none">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-white">Administrar preguntas</h1>
        <Link to="/" className="text-sm text-primario-300 hover:underline">
          Volver al inicio
        </Link>
      </header>

      <div className="mb-6">
        <FormularioPregunta textoBoton="Crear pregunta" onEnviar={crear} />
      </div>

      {error && <p className="mb-4 text-sm text-error">{error}</p>}

      {cargando && <PantallaCarga mensaje="Cargando preguntas…" />}

      {!cargando && preguntas.length === 0 && (
        <EstadoVacio titulo="No hay cartas todavía. ¡Crea la primera!" />
      )}

      {!cargando && preguntas.length > 0 && (
        <div className="flex flex-col gap-3">
          {preguntas.map((pregunta) => (
            <TarjetaPreguntaAdmin
              key={pregunta.id}
              pregunta={pregunta}
              onActualizar={actualizar}
              onEliminar={eliminar}
            />
          ))}
        </div>
      )}

      {hayMas && !cargando && preguntas.length > 0 && (
        <div className="mt-4 flex justify-center">
          <Boton
            variante="secundario"
            cargando={cargandoMas}
            onClick={() => cargarPagina(preguntas.length)}
          >
            Cargar más
          </Boton>
        </div>
      )}
    </div>
  )
}
