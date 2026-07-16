import { test, expect, request } from '@playwright/test'

// URL del backend (para sembrar preguntas antes de jugar). El frontend usa su
// propio VITE_API_URL; esto es sólo para el setup del test.
const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000'

test('modo práctica: 1 humano + 2 bots hasta el podio', async ({ browser }) => {
  // 1) La BD arranca sin preguntas. Una sala de práctica puede necesitar hasta
  //    3 robar_carta (una por ronda) antes de que el humano sea lector.
  const api = await request.newContext({ baseURL: API_URL })
  for (let i = 0; i < 3; i++) {
    const semilla = await api.post('/api/preguntas', {
      data: {
        enunciado: `¿Playa o montaña? (${i})`,
        opcion_1: `Playa ${i}`,
        opcion_2: `Montaña ${i}`,
      },
    })
    expect(semilla.ok(), 'no se pudo sembrar la pregunta (¿backend caído?)').toBeTruthy()
  }

  // 2) Un único navegador: el humano. Los otros 2 "jugadores" son bots del servidor.
  const contexto = await browser.newContext()
  const pagina = await contexto.newPage()
  const sufijo = Date.now().toString().slice(-6)
  const nombre = `practicante-${sufijo}`

  await pagina.goto('/')
  await pagina.fill('#campo-elige-un-nombre-de-usuario', nombre)
  await pagina.getByRole('button', { name: 'Crear usuario' }).click()
  await expect(pagina.getByRole('button', { name: 'Modo práctica' })).toBeVisible()

  // 3) "Modo práctica" crea la sala con el humano de anfitrión y 2 bots ya unidos.
  await pagina.getByRole('button', { name: 'Modo práctica' }).click()
  await pagina.waitForURL(/\/sala\/[A-Z0-9]{6}/)

  // 4) El lobby muestra a los 3 jugadores y llega a "3 conectados" cuando los
  //    bots terminan de conectarse por WebSocket (tarea en segundo plano).
  await expect(pagina.getByText('Jugadores (3 conectados)')).toBeVisible({ timeout: 20_000 })

  // 5) Con 3 conectados el gate del lobby ("mínimo 2") ya permite iniciar en solitario.
  await expect(pagina.getByRole('button', { name: 'Iniciar partida' })).toBeEnabled()
  await pagina.getByRole('button', { name: 'Iniciar partida' }).click()
  await expect(pagina.getByText(/^Turno de/).first()).toBeVisible()

  // 6) Jugamos rondas hasta que el humano haya sido lector al menos una vez.
  //    Con 3 jugadores y rotación módulo n, 3 rondas lo garantizan. Ramificamos
  //    por la UI visible (nunca asumiendo el rol localmente, igual que el cliente).
  let fueLector = false
  for (let ronda = 0; ronda < 3 && !fueLector; ronda++) {
    const botonRobar = pagina.getByRole('button', { name: 'Robar carta' })
    const esperandoLector = pagina.getByText('El lector está leyendo la carta…')
    // `isVisible()` no reintenta: el panel hijo (Robar carta / texto de espera) puede
    // pintarse en un commit de React posterior al de "Turno de …". Esperamos a que
    // cualquiera de las dos señales aparezca antes de decidir la rama.
    await Promise.race([
      botonRobar.waitFor({ state: 'visible', timeout: 15_000 }),
      esperandoLector.waitFor({ state: 'visible', timeout: 15_000 }),
    ])
    const esLector = await botonRobar.isVisible()

    if (esLector) {
      fueLector = true
      await pagina.getByRole('button', { name: 'Robar carta' }).click()
      await expect(pagina.getByText('¿Qué crees que votará el grupo?')).toBeVisible()
      await pagina.getByRole('button', { name: 'Todos eligen la Opción 1' }).click()
      await pagina.getByRole('button', { name: 'Confirmar predicción' }).click()

      // Los 2 bots votan solos (no forzamos nada); solo esperamos el resultado.
      await expect(pagina.getByText(/^(✅|❌)/)).toBeVisible({ timeout: 15_000 })
      await pagina.getByRole('button', { name: 'Siguiente turno' }).click()
    } else {
      // Un bot es el lector: roba y predice solo; nosotros votamos cuando se abre.
      await expect(pagina.getByRole('button', { name: 'Votar Opción 1' })).toBeVisible({
        timeout: 15_000,
      })
      await pagina.getByRole('button', { name: 'Votar Opción 1' }).click()
      await expect(pagina.getByText(/^(✅|❌)/)).toBeVisible({ timeout: 15_000 })
      // El bot lector dispara siguiente_turno solo. No verificamos aquí: "Turno de …"
      // está en pantalla durante TODA la ronda (no solo al empezar una nueva), así que
      // esperarlo no detectaría el cambio. La siguiente vuelta del for ya espera la
      // señal real de "ronda nueva" (Robar carta / El lector está leyendo).
    }
  }
  expect(fueLector, 'el humano nunca fue lector en 3 rondas').toBeTruthy()

  // 7) Finalizar y ver el podio con 3 filas (humano + 2 bots).
  await pagina.getByRole('button', { name: 'Finalizar partida' }).click()
  await pagina.getByRole('button', { name: 'Sí, terminar' }).click()
  await expect(pagina.getByText(/¡Ganador/)).toBeVisible()
  await expect(pagina.getByText(/— \d+ pts$/)).toHaveCount(3)

  await contexto.close()
  await api.dispose()
})
