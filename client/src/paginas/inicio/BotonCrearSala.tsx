import { useNavigate } from 'react-router-dom'
import Boton from '../../componentes/Boton'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { crearSala } from '../../store/slices/salaSlice'
import { uiActions } from '../../store/slices/uiSlice'

export default function BotonCrearSala() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const cargando = useAppSelector((state) => state.sala.cargando)

  async function manejarClic() {
    const resultado = await dispatch(crearSala())
    if (crearSala.fulfilled.match(resultado)) {
      navigate(`/sala/${resultado.payload.codigo}`)
    } else {
      dispatch(uiActions.notificar(resultado.payload ?? 'No se pudo crear la sala', 'error'))
    }
  }

  return (
    <Boton onClick={manejarClic} cargando={cargando} variante="primario">
      Crear sala
    </Boton>
  )
}
