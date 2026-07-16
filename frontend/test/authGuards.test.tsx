import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { navigationState, router } from './mocks/navigation'

const { useAuth } = vi.hoisted(() => ({ useAuth: vi.fn() }))

vi.mock('@/contexts/AuthContext', () => ({ useAuth }))

import AdminGuard from '@/components/admin/AdminGuard'
import AuthenticatedGuard from '@/components/auth/guards/AuthenticatedGuard'

describe('authenticated route guards', () => {
  beforeEach(() => {
    navigationState.pathname = '/profile'
  })

  it('redirects an unauthenticated profile visit back through login', async () => {
    useAuth.mockReturnValue({
      isAuthenticated: false,
      isAdmin: false,
      isInitializing: false,
    })

    render(
      <AuthenticatedGuard>
        <p>private profile</p>
      </AuthenticatedGuard>,
    )

    expect(screen.queryByText('private profile')).not.toBeInTheDocument()
    await waitFor(() => {
      expect(router.replace).toHaveBeenCalledWith('/login?from=%2Fprofile')
    })
  })

  it('renders an authenticated profile', () => {
    useAuth.mockReturnValue({
      isAuthenticated: true,
      isAdmin: false,
      isInitializing: false,
    })

    render(
      <AuthenticatedGuard>
        <p>private profile</p>
      </AuthenticatedGuard>,
    )

    expect(screen.getByText('private profile')).toBeInTheDocument()
  })

  it('keeps authenticated non-admin users out of admin content', () => {
    navigationState.pathname = '/admin'
    useAuth.mockReturnValue({
      isAuthenticated: true,
      isAdmin: false,
      isInitializing: false,
    })

    render(
      <AdminGuard>
        <p>admin content</p>
      </AdminGuard>,
    )

    expect(screen.getByText('Access Denied')).toBeInTheDocument()
    expect(screen.queryByText('admin content')).not.toBeInTheDocument()
  })

  it('renders admin content for an authenticated administrator', () => {
    navigationState.pathname = '/admin'
    useAuth.mockReturnValue({
      isAuthenticated: true,
      isAdmin: true,
      isInitializing: false,
    })

    render(
      <AdminGuard>
        <p>admin content</p>
      </AdminGuard>,
    )

    expect(screen.getByText('admin content')).toBeInTheDocument()
  })
})
