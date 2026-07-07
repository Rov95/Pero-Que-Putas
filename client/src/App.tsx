import { useEffect } from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Notificaciones from './componentes/Notificaciones'
import PantallaCarga from './componentes/PantallaCarga'
import PaginaInicio from './paginas/inicio/PaginaInicio'
import PaginaMarcador from './paginas/marcador/PaginaMarcador'
import PaginaPreguntas from './paginas/preguntas/PaginaPreguntas'
import PaginaSala from './paginas/sala/PaginaSala'
import { useAppDispatch, useAppSelector } from './store/hooks'
import { restaurarSesion } from './store/slices/sesionSlice'

const router = createBrowserRouter([
  { path: '/', element: <PaginaInicio /> },
  { path: '/sala/:codigo', element: <PaginaSala /> },
  { path: '/marcador', element: <PaginaMarcador /> },
  { path: '/preguntas', element: <PaginaPreguntas /> },
])

function App() {
  const dispatch = useAppDispatch()
  const restaurada = useAppSelector((state) => state.sesion.restaurada)

  useEffect(() => {
    dispatch(restaurarSesion())
  }, [dispatch])

  return (
    <>
      {restaurada ? (
        <RouterProvider router={router} />
      ) : (
        <PantallaCarga mensaje="Cargando…" />
      )}
      <Notificaciones />
    </>
  )
}

export default App
