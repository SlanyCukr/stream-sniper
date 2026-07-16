import { defineConfig, devices } from '@playwright/test'

const requiredDatabaseValue = (name: string) => {
  const value = process.env[name]
  if (!value) throw new Error(`Real E2E requires ${name}`)
  return value
}
const inheritedEnv = Object.fromEntries(
  Object.entries(process.env).filter((entry): entry is [string, string] => entry[1] !== undefined),
)
const backendEnv: Record<string, string> = {
  ...inheritedEnv,
  JWT_SECRET_KEY: process.env.JWT_SECRET_KEY ?? 'playwright-e2e-only-secret-at-least-32-characters',
  POSTGRES_USER: requiredDatabaseValue('POSTGRES_USER'),
  POSTGRES_PASSWORD: requiredDatabaseValue('POSTGRES_PASSWORD'),
  POSTGRES_HOST: requiredDatabaseValue('POSTGRES_HOST'),
  POSTGRES_DB: requiredDatabaseValue('POSTGRES_DB'),
  POSTGRES_PORT: requiredDatabaseValue('POSTGRES_PORT'),
  CACHE_WARM_ON_STARTUP: 'false',
}

export default defineConfig({
  testDir: './e2e',
  testMatch: 'real-api-boundary.spec.ts',
  forbidOnly: true,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'line' : 'list',
  use: {
    baseURL: 'http://localhost:4174',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: 'uv run uvicorn stream_sniper.api.asgi:app --host 127.0.0.1 --port 5002',
      cwd: '../backend',
      url: 'http://localhost:5002/docs',
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: 'ignore',
      stderr: 'ignore',
      env: backendEnv,
    },
    {
      command: 'npx next dev --turbopack -p 4174',
      url: 'http://localhost:4174/login',
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: 'ignore',
      stderr: 'ignore',
      env: {
        ...process.env,
        API_PROXY_TARGET: 'http://localhost:5002',
      },
    },
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
