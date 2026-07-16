import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, vi } from 'vitest'

import { resetNavigationMocks } from './mocks/navigation'
import { server } from './mocks/server'

vi.mock('next/navigation', async () => {
  const { navigationState, router } = await import('./mocks/navigation')

  return {
    notFound: vi.fn(),
    redirect: vi.fn(),
    usePathname: () => navigationState.pathname,
    useRouter: () => router,
    useSearchParams: () => navigationState.searchParams,
  }
})

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  server.resetHandlers()
  resetNavigationMocks()
  cleanup()
  localStorage.clear()
})
afterAll(() => server.close())
