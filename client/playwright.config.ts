import { defineConfig } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:5173'

// Usa el Chrome del sistema (canal 'chrome'); no descarga navegadores.
export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.ts',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: BASE_URL,
    channel: 'chrome',
    launchOptions: { args: ['--no-sandbox'] },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  // Arranca el frontend (Vite) automáticamente. El backend debe estar corriendo
  // aparte (lo hace scripts/e2e.sh). reuseExistingServer: si ya hay un Vite en
  // :5173, lo reutiliza en vez de arrancar otro.
  webServer: {
    command: 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
