import { test, expect, request, type Page } from '@playwright/test'

// URL del backend (para sembrar una pregunta antes de jugar). El frontend usa su
// propio VITE_API_URL; esto es sólo para el setup del test.
const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000'

async function registrar(pagina: Page, nombre: string): Promise<void> {
  await pagina.goto('/')
  await pagina.fill('#campo-elige-un-nombre-de-usuario', nombre)
  await pagina.getByRole('button', { name: 'Crear usuario' }).click()
  await expect(pagina.getByRole('button', { name: 'Crear sala' })).toBeVisible()
}

test('partida completa de 3 jugadores: registro → sala → ronda → podio → marcador', async ({
  browser,
}) => {
  // 1) La BD arranca sin preguntas: sembramos una o el juego no puede robar carta.
  const api = await request.newContext({ baseURL: API_URL })
  const semilla = await api.post('/api/preguntas', {
    data: {
      enunciado: '¿Qué prefieres este fin de semana?',
      opcion_1: 'Bailar toda la noche',
      opcion_2: 'Dormir todo el día',
    },
  })
  expect(semilla.ok(), 'no se pudo sembrar la pregunta (¿backend caído?)').toBeTruthy()

  // 2) Tres navegadores independientes (localStorage separado por contexto).
  const sufijo = Date.now().toString().slice(-6)
  const nombres = [`ana-${sufijo}`, `bruno-${sufijo}`, `caro-${sufijo}`]
  const contextos = await Promise.all(nombres.map(() => browser.newContext()))
  const paginas = await Promise.all(contextos.map((c) => c.newPage()))
  for (let i = 0; i < paginas.length; i++) {
    await registrar(paginas[i], nombres[i])
  }
  const [anfitrion, ...invitados] = paginas
  const nombreDe = new Map<Page, string>(paginas.map((p, i) => [p, nombres[i]]))

  // 3) El anfitrión crea la sala y saca el código de la URL.
  await anfitrion.getByRole('button', { name: 'Crear sala' }).click()
  await anfitrion.waitForURL(/\/sala\/[A-Z0-9]{6}/)
  const codigo = new URL(anfitrion.url()).pathname.split('/').pop()!

  // 4) Los otros dos se unen con el código.
  for (const invitado of invitados) {
    await invitado.fill('input[placeholder="ABC123"]', codigo)
    await invitado.getByRole('button', { name: 'Unirse a la sala' }).click()
    await invitado.waitForURL(new RegExp(`/sala/${codigo}`))
  }

  // 5) El anfitrión ve a los 3 conectados (vía WebSocket) e inicia la partida.
  await expect(anfitrion.getByText('Jugadores (3 conectados)')).toBeVisible({ timeout: 20_000 })
  await anfitrion.getByRole('button', { name: 'Iniciar partida' }).click()
  for (const pagina of paginas) {
    await expect(pagina.getByText(/^Turno de/).first()).toBeVisible()
  }

  // 6) El lector es la única página que ve el botón "Robar carta".
  let lector: Page | undefined
  await expect(async () => {
    for (const pagina of paginas) {
      if (await pagina.getByRole('button', { name: 'Robar carta' }).count()) {
        lector = pagina
        return
      }
    }
    throw new Error('todavía no aparece "Robar carta"')
  }).toPass({ timeout: 15_000 })
  const nombreLector = nombreDe.get(lector!)!
  const votantes = paginas.filter((pagina) => pagina !== lector)

  // 7) Ronda: robar carta → predecir "Todos eligen la Opción 1" → confirmar.
  // La carta robada es aleatoria entre todas las preguntas de la BD, así que solo
  // comprobamos que la carta muestra UN enunciado (no cuál).
  await lector!.getByRole('button', { name: 'Robar carta' }).click()
  await expect(lector!.getByTestId('enunciado-carta')).not.toBeEmpty()
  await expect(lector!.getByText('¿Qué crees que votará el grupo?')).toBeVisible()
  await lector!.getByRole('button', { name: 'Todos eligen la Opción 1' }).click()
  await lector!.getByRole('button', { name: 'Confirmar predicción' }).click()

  // 8) Los dos votantes eligen la Opción 1 (coincide con la predicción).
  for (const votante of votantes) {
    await votante.getByRole('button', { name: 'Votar Opción 1' }).click()
  }

  // 9) Predijo todos_1 y todos votaron 1 → acierto → +1 punto para el lector.
  await expect(lector!.getByText(`✅ +1 punto para ${nombreLector}`)).toBeVisible()

  // 10) El anfitrión finaliza la partida.
  await anfitrion.getByRole('button', { name: 'Finalizar partida' }).click()
  await anfitrion.getByRole('button', { name: 'Sí, terminar' }).click()

  // 11) Todas las páginas llegan al podio; el lector gana con 1 punto.
  for (const pagina of paginas) {
    await expect(pagina.getByText(/¡Ganador/)).toBeVisible()
  }
  await expect(anfitrion.getByText(`🏆 ${nombreLector} — 1 pts`)).toBeVisible()

  // 12) El marcador histórico registra al lector.
  await lector!.goto('/marcador')
  await expect(
    lector!.getByRole('heading', { name: 'Marcador histórico' }),
  ).toBeVisible()
  await expect(lector!.getByText(nombreLector)).toBeVisible()

  await Promise.all(contextos.map((c) => c.close()))
  await api.dispose()
})
