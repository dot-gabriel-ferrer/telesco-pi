import { expect, test } from '@playwright/test'

test('mobile observation: connect, preview, configure, capture, download and STOP', async ({ page, request }) => {
  await request.post('/api/v1/devices/camera.primary/disconnect')
  await request.post('/api/v1/devices/mount.primary/disconnect')
  const sessions = await (await request.get('/api/v1/sessions')).json()
  for (const session of sessions.items) {
    if (session.status === 'active') await request.post(`/api/v1/sessions/${session.id}/close`)
  }
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('La noche es tuya')
  await page.getByRole('button', { name: 'Conectar montura', exact: true }).click()
  await page.getByRole('button', { name: 'Conectar cámara', exact: true }).click()
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Cerrar sesión', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Iniciar preview', exact: true }).click()
  await expect(page.getByAltText('Previsualización actual de la cámara')).toBeVisible()
  const filesBefore = (await (await request.get('/api/v1/sessions/files')).json()).items.length
  await expect.poll(async () => page.locator('.preview-frame img').evaluate(
    (image: HTMLImageElement) => image.naturalWidth,
  )).toBe(640)
  expect((await (await request.get('/api/v1/sessions/files')).json()).items.length).toBe(filesBefore)
  await page.getByRole('link', { name: 'Captura', exact: true }).click()
  await page.getByLabel('Exposición (ms)').fill('20')
  await page.getByLabel('Ganancia', { exact: true }).fill('120')
  await page.getByRole('button', { name: 'Aplicar parámetros', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Parámetros aplicados')
  await page.getByRole('button', { name: 'Capturar imagen', exact: true }).click()
  await expect(page.getByText('Captura guardada.')).toBeVisible()
  await page.getByRole('link', { name: 'Archivos', exact: true }).click()
  const download = page.waitForEvent('download')
  await page.getByRole('link', { name: /Descargar.*_preview\.png/ }).first().click()
  expect((await download).suggestedFilename()).toMatch(/_preview\.png$/)
  await page.getByRole('link', { name: 'Control', exact: true }).click()
  await page.getByRole('button', { name: 'Subir', exact: true }).click()
  await page.getByRole('button', { name: 'STOP', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('stopped')
  await page.getByRole('button', { name: 'Modo noche', exact: true }).click()
  await expect(page.locator('.app-shell')).toHaveClass(/night-mode/)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('responsive navigation, settings focus and visible hardware errors', async ({ page, request }) => {
  await page.goto('/')
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await expect(page.getByRole('button', { name: 'STOP montura', exact: true })).toBeVisible()
  }
  await page.getByRole('button', { name: 'Abrir menú lateral' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'Abrir menú lateral' })).toBeFocused()
  await request.post('/api/v1/devices/mount.primary/fault', { data: { fault: { mode: 'disconnect' } } })
  await page.getByRole('button', { name: 'STOP montura', exact: true }).click()
  // A rejected/disconnected operation must not disappear behind a success toast.
  await expect(page.getByRole('alert')).toBeVisible()
  await request.post('/api/v1/devices/mount.primary/fault', { data: { fault: { mode: 'recover' } } })
})

test('installed application shell loads offline without pretending hardware is available', async ({ page, context }) => {
  await page.goto('/')
  await page.evaluate(() => navigator.serviceWorker.ready)
  await page.reload()
  await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true)
  try {
    await context.setOffline(true)
    await page.reload()
    await expect(page.getByRole('heading', { level: 1 })).toContainText('La noche es tuya')
    await expect(page.getByText('Backend no disponible. Comprueba el servicio local y la conexión.')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Iniciar sesión', exact: true })).toBeDisabled()
  } finally {
    await context.setOffline(false)
  }
})

test('local catalog and night planner use the active session', async ({ page, request }) => {
  await request.post('/api/v1/sessions', { data: { name: 'Planner browser test' } })
  await page.goto('/plan')
  await page.getByRole('checkbox').first().click()
  await page.getByRole('button', { name: /Generar plan de noche/ }).click()
  await expect(page.getByRole('heading', { name: 'Plan generado' })).toBeVisible()
  await expect(page.getByRole('alert')).not.toBeVisible()
})

test('planetary processing selects indexed originals and downloads PNG16', async ({ page, request }) => {
  const session = (await (await request.post('/api/v1/sessions', { data: { name: 'Planetary browser' } })).json()).session
  await request.post('/api/v1/devices/camera.primary/connect')
  for (let index = 0; index < 4; index++) {
    const capture = await request.post('/api/v1/devices/camera/capture', { data: { session_id: session.id } })
    expect(capture.ok()).toBe(true)
  }
  await page.goto('/files')
  await expect(page.getByRole('checkbox', { name: /^Seleccionar / })).toHaveCount(4)
  for (const checkbox of await page.getByRole('checkbox', { name: /^Seleccionar / }).all()) await checkbox.check()
  await page.getByRole('button', { name: 'Apilar 4 capturas', exact: true }).click()
  await expect(page.getByText('Apilado completado: 2 de 4 frames.')).toBeVisible()
  await expect(page.getByAltText('Resultado del apilado planetario en luminancia')).toBeVisible()
  const download = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Descargar resultado PNG16', exact: true }).click()
  expect((await download).suggestedFilename()).toMatch(/^planetary_.*\.png$/)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
