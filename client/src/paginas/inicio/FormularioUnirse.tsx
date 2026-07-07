import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import Boton from '../../componentes/Boton'
import CampoTexto from '../../componentes/CampoTexto'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { unirseSala } from '../../store/slices/salaSlice'
import { esCodigoSalaCompleto, normalizarCodigoSala } from '../../utilidades/codigoSala'

export default function FormularioUnirse() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const { cargando, error } = useAppSelector((state) => state.sala)
  const [codigo, setCodigo] = useState('')

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault()
    if (!esCodigoSalaCompleto(codigo)) return
    const resultado = await dispatch(unirseSala(codigo))
    if (unirseSala.fulfilled.match(resultado)) {
      navigate(`/sala/${resultado.payload.codigo}`)
    }
  }

  return (
    <form onSubmit={manejarEnvio} className="flex w-full max-w-sm flex-col gap-4">
      <CampoTexto
        etiqueta="Código de sala"
        value={codigo}
        onChange={(evento) => setCodigo(normalizarCodigoSala(evento.target.value))}
        placeholder="ABC123"
        maxLength={6}
        error={error}
        className="text-center font-display text-2xl tracking-[0.3em] uppercase"
        autoComplete="off"
        inputMode="text"
      />
      <Boton
        type="submit"
        cargando={cargando}
        disabled={!esCodigoSalaCompleto(codigo)}
        variante="secundario"
      >
        Unirse a la sala
      </Boton>
    </form>
  )
}
