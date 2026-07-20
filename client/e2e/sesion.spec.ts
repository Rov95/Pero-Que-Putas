import { test, expect } from '@playwright/test'

test('cerrar sesión revoca el token y permite volver a entrar por nombre', async ({ browser }) => {
  const contexto = await browser.newContext()
  const pagina = await contexto.newPage()
  const sufijo = Date.now().toString().slice(-6)
  const nombre = `saliente-${sufijo}`

  // 1) Registro: guarda el token de sesión y muestra el menú principal.
  await pagina.goto('/')
  await pagina.fill('#campo-elige-un-nombre-de-usuario', nombre)
  await pagina.getByRole('button', { name: 'Crear usuario' }).click()
  await expect(pagina.getByRole('button', { name: 'Modo práctica' })).toBeVisible()
  const token = await pagina.evaluate(() => localStorage.getItem('pqp_token'))
  expect(token).toBeTruthy()

  // 2) Cerrar sesión: vuelve al registro y limpia todo el almacenamiento pqp_*.
  await pagina.getByRole('button', { name: 'Cerrar sesión' }).click()
  await expect(pagina.getByRole('button', { name: 'Crear usuario' })).toBeVisible()
  const almacen = await pagina.evaluate(() => ({
    token: localStorage.getItem('pqp_token'),
    usuarioId: localStorage.getItem('pqp_usuario_id'),
    username: localStorage.getItem('pqp_username'),
    salaCodigo: localStorage.getItem('pqp_sala_codigo'),
  }))
  expect(almacen).toEqual({ token: null, usuarioId: null, username: null, salaCodigo: null })

  // 3) Recargar no resucita la sesión (el token ya no está).
  await pagina.reload()
  await expect(pagina.getByRole('button', { name: 'Crear usuario' })).toBeVisible()

  // 4) Volver a entrar por nombre, sin contraseña, con el modo login del formulario.
  await pagina.getByRole('button', { name: '¿Ya tienes usuario? Entra con tu nombre' }).click()
  await pagina.fill('#campo-tu-nombre-de-usuario', nombre)
  await pagina.getByRole('button', { name: 'Iniciar sesión' }).click()
  await expect(pagina.getByRole('button', { name: 'Modo práctica' })).toBeVisible()
  await expect(pagina.getByText(nombre)).toBeVisible()
  const tokenNuevo = await pagina.evaluate(() => localStorage.getItem('pqp_token'))
  expect(tokenNuevo).toBeTruthy()
  expect(tokenNuevo).not.toBe(token)

  await contexto.close()
})
