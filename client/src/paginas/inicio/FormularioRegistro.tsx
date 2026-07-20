import { useState, type FormEvent } from 'react'
import Boton from '../../componentes/Boton'
import CampoTexto from '../../componentes/CampoTexto'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { crearUsuario, iniciarSesion, sesionActions } from '../../store/slices/sesionSlice'

type Modo = 'registro' | 'login'

function validar(username: string): string | null {
  if (username.length < 3 || username.length > 30) return 'Debe tener entre 3 y 30 caracteres'
  if (/\s/.test(username)) return 'No puede contener espacios'
  return null
}

export default function FormularioRegistro() {
  const dispatch = useAppDispatch()
  const { cargando, error, errorEstado } = useAppSelector((state) => state.sesion)
  const [modo, setModo] = useState<Modo>('registro')
  const [username, setUsername] = useState('')
  const [errorLocal, setErrorLocal] = useState<string | null>(null)

  // El nombre ya existe: además del error se ofrece entrar directamente con él.
  const nombreOcupado = modo === 'registro' && errorEstado === 409

  function manejarEnvio(evento: FormEvent) {
    evento.preventDefault()
    const problema = validar(username)
    setErrorLocal(problema)
    if (problema) return
    if (modo === 'registro') {
      dispatch(crearUsuario(username))
    } else {
      dispatch(iniciarSesion(username))
    }
  }

  function cambiarModo() {
    setModo(modo === 'registro' ? 'login' : 'registro')
    setErrorLocal(null)
    dispatch(sesionActions.limpiarErrorSesion())
  }

  return (
    <form onSubmit={manejarEnvio} className="flex w-full max-w-sm flex-col gap-4">
      <CampoTexto
        etiqueta={modo === 'registro' ? 'Elige un nombre de usuario' : 'Tu nombre de usuario'}
        value={username}
        onChange={(evento) => setUsername(evento.target.value)}
        placeholder="p. ej. martina"
        error={errorLocal ?? error}
        maxLength={30}
        autoComplete="off"
      />
      <Boton type="submit" cargando={cargando}>
        {modo === 'registro' ? 'Crear usuario' : 'Iniciar sesión'}
      </Boton>

      {nombreOcupado && (
        <Boton
          type="button"
          variante="secundario"
          cargando={cargando}
          onClick={() => dispatch(iniciarSesion(username))}
        >
          Iniciar sesión como {username}
        </Boton>
      )}

      <button
        type="button"
        onClick={cambiarModo}
        className="text-sm text-white/50 underline-offset-4 hover:text-white hover:underline"
      >
        {modo === 'registro'
          ? '¿Ya tienes usuario? Entra con tu nombre'
          : '¿No tienes usuario? Créalo aquí'}
      </button>
    </form>
  )
}
