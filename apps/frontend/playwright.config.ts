import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    viewport: { width: 390, height: 844 },
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: '.venv/bin/python -m uvicorn apps.backend.app.main:app --host 127.0.0.1 --port 8000',
      cwd: '../..',
      url: 'http://127.0.0.1:8000/api/v1/health/live',
      reuseExistingServer: false,
      env: { TELESCO_PI_ENVIRONMENT: 'test', TELESCO_PI_DATA_DIR: '.runtime-data/e2e', TELESCO_PI_DEVICE_MODE: 'simulator' },
    },
    {
      command: 'npm run build && npm run preview -- --host 127.0.0.1 --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
    },
  ],
})
