import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { salaActions, sincronizarSala, unirseSala } from '../../store/slices/salaSlice'
import { uiActions } from '../../store/slices/uiSlice'
import { almacenamiento } from '../../utilidades/almacenamiento'

export function useConexionSala(codigo: string) {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const miId = useAppSelector((state) => state.sesion.usuario?.id)
  const motivoExpulsion = useAppSelector((state) => state.sala.motivoExpulsion)
  const errorJuego = useAppSelector((state) => state.sala.errorJuego)

  useEffect(() => {
    if (!codigo || !miId) return
    let activo = true

    async function conectar() {
      const resultadoUnion = await dispatch(unirseSala(codigo))
      if (!activo) return

      if (unirseSala.fulfilled.match(resultadoUnion)) {
        await dispatch(sincronizarSala(codigo))
        if (!activo) return
      } else {
        // El backend rechaza "unirse" con 409 en cuanto la sala deja de estar "esperando",
        // incluso si ya somos miembros (revisa el estado antes que la membresía). Puede
        // pasar tras recargar la pestaña a mitad de partida: resincronizamos para comprobar
        // si igual pertenecemos antes de rendirnos.
        const resultadoSync = await dispatch(sincronizarSala(codigo))
        if (!activo) return
        if (!sincronizarSala.fulfilled.match(resultadoSync)) return

        const soyMiembro = resultadoSync.payload.jugadores.some((j) => j.usuario_id === miId)
        if (!soyMiembro) {
          dispatch(uiActions.notificar('La partida ya empezó', 'error'))
          navigate('/')
          return
        }
      }

      almacenamiento.guardarSalaCodigo(codigo)
      dispatch(salaActions.conectarWs(codigo))
    }
    void conectar()

    return () => {
      activo = false
      dispatch(salaActions.desconectarWs())
    }
  }, [codigo, dispatch, miId, navigate])

  useEffect(() => {
    if (!motivoExpulsion) return
    dispatch(uiActions.notificar(motivoExpulsion, 'error'))
    almacenamiento.eliminarSalaCodigo()
    navigate('/')
  }, [motivoExpulsion, dispatch, navigate])

  useEffect(() => {
    if (!errorJuego) return
    dispatch(uiActions.notificar(errorJuego, 'error'))
    dispatch(salaActions.limpiarErrorJuego())
  }, [errorJuego, dispatch])
}
