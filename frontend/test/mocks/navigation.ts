import { vi } from 'vitest'

export const router = {
  back: vi.fn(),
  forward: vi.fn(),
  prefetch: vi.fn(),
  push: vi.fn(),
  refresh: vi.fn(),
  replace: vi.fn(),
}

export const navigationState = {
  pathname: '/',
  searchParams: new URLSearchParams(),
}

export function resetNavigationMocks() {
  Object.values(router).forEach((mock) => mock.mockReset())
  navigationState.pathname = '/'
  navigationState.searchParams = new URLSearchParams()
}
