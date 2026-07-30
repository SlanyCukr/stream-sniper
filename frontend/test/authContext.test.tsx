import { act, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  api,
  postJson,
  putJson,
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
    postJson: vi.fn(),
    putJson: vi.fn(),
    removeUnauthorizedInterceptor: remove,
    installUnauthorizedInterceptor: vi.fn(() => remove),
  }
})

vi.mock('@/lib/api/client', () => ({
  api,
  postJson,
  putJson,
  installUnauthorizedInterceptor,
}))

import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { requestPasswordChange, updateProfile } from '@/lib/auth/service'
import { SessionStorageError } from '@/lib/auth/session'
import SessionErrorAlert from '@/components/auth/SessionErrorAlert'

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
    postJson.mockResolvedValueOnce({ access_token: validToken })
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
    postJson.mockResolvedValueOnce({ access_token: validToken })
    api.get.mockResolvedValueOnce({
      data: {
        id: 7,
        username: 'operator',
        email: 'operator@example.test',
        role: 'admin',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
      },
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
    expect(screen.getByTestId('session')).toHaveTextContent('"isActive":true')
    expect(screen.getByTestId('session')).not.toHaveTextContent('is_active')
    expect(localStorage.getItem('token')).toBe(validToken)
  })

  it('removes its unauthorized interceptor when the provider unmounts', () => {
    const { unmount } = render(
      <AuthProvider>
        <SessionErrorAlert />
        <AuthProbe />
      </AuthProvider>,
    )

    const installsBeforeUnmount = installUnauthorizedInterceptor.mock.calls.length
    unmount()
    expect(removeUnauthorizedInterceptor).toHaveBeenCalledTimes(installsBeforeUnmount)
  })

  it('finishes initialization and reports contextual storage read failures', async () => {
    const storageError = new DOMException('storage denied', 'SecurityError')
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const getItem = vi.spyOn(Storage.prototype, 'getItem')
      .mockImplementationOnce(() => { throw storageError })

    render(
      <AuthProvider>
        <SessionErrorAlert />
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('session')).toHaveTextContent('"isInitializing":false')
    })
    expect(screen.getByTestId('session')).toHaveTextContent(
      'Unable to read stored authentication session',
    )
    expect(screen.getByText('Session problem')).toBeInTheDocument()
    await act(async () => {
      screen.getByRole('button', { name: 'Close alert' }).click()
    })
    await waitFor(() => {
      expect(screen.queryByText('Session problem')).not.toBeInTheDocument()
    })
    expect(screen.getByTestId('session')).toHaveTextContent('"isAuthenticated":false')
    expect(consoleError).toHaveBeenCalledWith(
      'Unable to restore session',
      expect.any(SessionStorageError),
    )
    const loggedError = consoleError.mock.calls[0]?.[1]
    expect(loggedError).toBeInstanceOf(SessionStorageError)
    expect((loggedError as SessionStorageError).cause).toBe(storageError)
    getItem.mockRestore()
    consoleError.mockRestore()
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
    putJson.mockResolvedValueOnce({ message: 'password changed' })

    await expect(requestPasswordChange('old-secret', 'new-secret')).resolves.toEqual({
      message: 'password changed',
    })
  })

  it('rejects malformed authentication success payloads at the service boundary', async () => {
    postJson.mockResolvedValueOnce({ access_token: 7 })

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )
    await act(async () => {
      screen.getByRole('button', { name: 'login' }).click()
    })
    await waitFor(() => expect(screen.getByTestId('result')).toHaveTextContent('"success":false'))
    expect(api.get).not.toHaveBeenCalled()

    putJson.mockResolvedValueOnce({ message: 42 })
    await expect(requestPasswordChange('old-secret', 'new-secret')).rejects.toThrow(
      'password change response.message must be a string',
    )
  })

  it('maps profile updates to the authenticated-user domain model', async () => {
    api.put.mockResolvedValueOnce({
      data: {
        id: 7,
        username: 'operator',
        email: 'new@example.test',
        role: 'admin',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
      },
    })

    await expect(updateProfile({ email: 'new@example.test' })).resolves.toEqual({
      id: 7,
      username: 'operator',
      email: 'new@example.test',
      role: 'admin',
      isActive: true,
      createdAt: '2026-01-01T00:00:00Z',
    })
  })
})
