import { act, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  api,
  removeUnauthorizedInterceptor,
  installUnauthorizedInterceptor,
} = vi.hoisted(() => {
  const remove = vi.fn()
  return {
    api: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
    },
    removeUnauthorizedInterceptor: remove,
    installUnauthorizedInterceptor: vi.fn(() => remove),
  }
})

vi.mock('@/lib/api/client', () => ({
  api,
  installUnauthorizedInterceptor,
}))

import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { requestPasswordChange } from '@/lib/auth/service'

const validToken = [
  'eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0',
  btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })),
  'signature',
].join('.')

function AuthProbe() {
  const auth = useAuth()
  const [result, setResult] = useState<unknown>(null)

  return (
    <>
      <button
        type="button"
        onClick={async () => {
          try {
            await auth.login('operator', 'secret')
            setResult({ success: true })
          } catch (error) {
            const authError = error as Error & { response?: { status?: number } }
            setResult({
              success: false,
              message: authError.message,
              status: authError.response?.status,
            })
          }
        }}
      >
        login
      </button>
      <output data-testid="result">{JSON.stringify(result)}</output>
      <output data-testid="session">
        {JSON.stringify({
          isInitializing: auth.isInitializing,
          isAuthenticated: auth.isAuthenticated,
          user: auth.user,
          sessionError: auth.sessionError,
        })}
      </output>
    </>
  )
}

describe('AuthProvider session boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('reports login failure and leaves no session when profile hydration fails', async () => {
    api.post.mockResolvedValueOnce({ data: { access_token: validToken } })
    api.get.mockRejectedValueOnce(Object.assign(new Error('profile unavailable'), {
      response: { status: 503 },
    }))

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await act(async () => {
      screen.getByRole('button', { name: 'login' }).click()
    })

    await waitFor(() => {
      expect(screen.getByTestId('result')).toHaveTextContent('"success":false')
    })
    expect(screen.getByTestId('result')).toHaveTextContent('"message":"profile unavailable"')
    expect(screen.getByTestId('result')).toHaveTextContent('"status":503')
    expect(screen.getByTestId('session')).toHaveTextContent('"isAuthenticated":false')
    expect(screen.getByTestId('session')).toHaveTextContent('"user":null')
    expect(screen.getByTestId('session')).toHaveTextContent('"sessionError":null')
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('publishes the session only after the profile is available', async () => {
    api.post.mockResolvedValueOnce({ data: { access_token: validToken } })
    api.get.mockResolvedValueOnce({
      data: { id: 7, username: 'operator', role: 'admin' },
    })

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await act(async () => {
      screen.getByRole('button', { name: 'login' }).click()
    })

    await waitFor(() => {
      expect(screen.getByTestId('result')).toHaveTextContent('"success":true')
    })
    expect(screen.getByTestId('session')).toHaveTextContent('"isAuthenticated":true')
    expect(localStorage.getItem('token')).toBe(validToken)
  })

  it('removes its unauthorized interceptor when the provider unmounts', () => {
    const { unmount } = render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    const installsBeforeUnmount = installUnauthorizedInterceptor.mock.calls.length
    unmount()
    expect(removeUnauthorizedInterceptor).toHaveBeenCalledTimes(installsBeforeUnmount)
  })

  it('finishes initialization and reports contextual storage read failures', async () => {
    const storageError = new DOMException('storage denied', 'SecurityError')
    const getItem = vi.spyOn(Storage.prototype, 'getItem')
      .mockImplementationOnce(() => { throw storageError })

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('session')).toHaveTextContent('"isInitializing":false')
    })
    expect(screen.getByTestId('session')).toHaveTextContent(
      'Unable to read stored authentication session',
    )
    expect(screen.getByTestId('session')).toHaveTextContent('"isAuthenticated":false')
    getItem.mockRestore()
  })

  it('clears in-memory session state when persistent cleanup fails', async () => {
    localStorage.setItem('token', validToken)
    api.get.mockRejectedValueOnce(new Error('profile unavailable'))
    const removeItem = vi.spyOn(Storage.prototype, 'removeItem')
      .mockImplementationOnce(() => { throw new DOMException('storage denied', 'SecurityError') })

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('session')).toHaveTextContent('"isInitializing":false')
    })
    expect(screen.getByTestId('session')).toHaveTextContent(
      'Unable to clear stored authentication session',
    )
    expect(screen.getByTestId('session')).toHaveTextContent('"isAuthenticated":false')
    expect(localStorage.getItem('token')).toBe(validToken)
    removeItem.mockRestore()
  })

  it('unwraps the password-change response at the auth service boundary', async () => {
    api.put.mockResolvedValueOnce({ data: { message: 'password changed' } })

    await expect(requestPasswordChange('old-secret', 'new-secret')).resolves.toEqual({
      message: 'password changed',
    })
  })
})
