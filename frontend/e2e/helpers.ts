import { expect, type Page, type Route } from '@playwright/test'

/** Fulfills a mocked route with a JSON body — the shared shape every spec's route handler returns. */
export const json = (route: Route, body: unknown, status = 200) => route.fulfill({
  status,
  contentType: 'application/json',
  body: JSON.stringify(body),
})

/** 500-fallback for any route branch a spec's handler didn't expect to hit. */
export const unexpected = (route: Route, pathname: string) => json(
  route,
  { detail: `Unexpected smoke request: ${route.request().method()} ${pathname}` },
  500,
)

/** Toggles a pressed/unpressed filter pill, asserting the aria-pressed state on both sides of the click. */
export const clickPill = async (page: Page, name: string) => {
  const pill = page.getByRole('button', { name })
  await expect(pill).toHaveAttribute('aria-pressed', 'false')
  await pill.click()
  await expect(pill).toHaveAttribute('aria-pressed', 'true')
}

/** Fills the login form and submits it — assumes the page is already on /login. */
export const login = async (page: Page, username: string, password: string) => {
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Login' }).click()
}
