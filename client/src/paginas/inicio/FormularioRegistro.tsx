import { useState, type FormEvent } from 'react'
import Boton from '../../componentes/Boton'
import CampoTexto from '../../componentes/CampoTexto'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { crearUsuario } from '../../store/slices/sesionSlice'

function validar(username: string): string | null {
  if (username.length < 3 || username.length > 30) return 'Debe tener entre 3 y 30 caracteres'
  if (/\s/.test(username)) return 'No puede contener espacios'
  return null
}

export default function FormularioRegistro() {
  const dispatch = useAppDispatch()
  const { cargando, error } = useAppSelector((state) => state.sesion)
  const [username, setUsername] = useState('')
  const [errorLocal, setErrorLocal] = useState<string | null>(null)

  function manejarEnvio(evento: FormEvent) {
    evento.preventDefault()
    const problema = validar(username)
    setErrorLocal(problema)
    if (problema) return
    dispatch(crearUsuario(username))
  }

  return (
    <form onSubmit={manejarEnvio} className="flex w-full max-w-sm flex-col gap-4">
      <CampoTexto
        etiqueta="Elige un nombre de usuario"
        value={username}
        onChange={(evento) => setUsername(evento.target.value)}
        placeholder="p. ej. martina"
        error={errorLocal ?? error}
        maxLength={30}
        autoComplete="off"
      />
      <Boton type="submit" cargando={cargando}>
        Crear usuario
      </Boton>
    </form>
  )
}
