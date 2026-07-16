import { expect, test } from '@playwright/test'
import { execFileSync } from 'node:child_process'

test.beforeAll(() => {
  execFileSync('../backend/.venv/bin/python', ['e2e/seed_real_analytics.py'], {
    cwd: process.cwd(),
    env: process.env,
    stdio: 'inherit',
  })
})

const adminPassword = process.env.E2E_ADMIN_LOGIN_VALUE
if (!adminPassword) throw new Error('Real E2E requires E2E_ADMIN_LOGIN_VALUE')

test('registers through FastAPI and performs an authenticated password change', async ({ page }) => {
  const suffix = Date.now().toString()
  const username = `e2e_${suffix}`
  const password = 'SmokePass123!'
  const changedPassword = 'ChangedPass456!'

  await page.goto('/login')
  await page.getByRole('button', { name: "Don't have an account? Register here" }).click()
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Email').fill(`${username}@gmail.com`)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByLabel('Confirm Password').fill(password)
  await page.getByRole('button', { name: 'Create Account' }).click()

  await expect(page.getByRole('button', { name: 'User menu' })).toContainText(username)
  await page.goto('/profile')
  await expect(page.getByRole('heading', { name: 'User Profile' })).toBeVisible()

  await page.getByRole('button', { name: 'Change Password' }).click()
  await page.getByLabel('Current Password').fill(password)
  await page.getByLabel('New Password', { exact: true }).fill(changedPassword)
  await page.getByLabel('Confirm New Password').fill(changedPassword)
  await page.getByRole('button', { name: 'Change Password' }).last().click()

  await expect(page.getByText('Password changed successfully!')).toBeVisible()
})

test('renders seeded stream analytics through Next and FastAPI', async ({ page }) => {
  await page.goto('/stream/990002')

  await expect(page.getByRole('heading', { name: 'E2E Operator' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Deterministic Analytics Stream' })).toBeVisible()
  await expect(page.locator('dt', { hasText: 'Messages' }).locator('xpath=following-sibling::dd[1]')).toHaveText('7')
  await expect(page.getByText('real boundary message')).toBeVisible()
})

test('persists an admin tracking mutation through the real stack', async ({ page }) => {
  await page.goto('/login?from=/admin/tracking/streamers')
  await page.getByLabel('Username').fill('e2e_admin')
  await page.getByLabel('Password').fill(adminPassword)
  await page.getByRole('button', { name: 'Login' }).click()

  await expect(page).toHaveURL(/\/admin\/tracking\/streamers$/)
  const row = page.getByRole('row').filter({ hasText: 'e2e_operator' })
  await row.getByRole('button', { name: 'Deactivate' }).click()
  await expect(page.getByText('Streamer updated successfully')).toBeVisible()

  await page.reload()
  await expect(page.getByRole('row').filter({ hasText: 'e2e_operator' }).getByRole('button', { name: 'Activate' })).toBeVisible()
})
