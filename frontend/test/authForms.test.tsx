import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const auth = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
  updateUser: vi.fn(),
  changePassword: vi.fn(),
  error: null as string | null,
  isAuthenticated: false,
  user: {
    username: 'operator',
    email: 'old@example.test',
    role: 'user',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  },
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    ...auth,
    isInitializing: false,
  }),
}))

import LoginForm from '@/components/auth/login/LoginForm'
import PasswordChangeModal from '@/components/auth/password/PasswordChangeModal'
import UserProfile from '@/components/auth/profile/UserProfile'
import Login from '@/views/auth/Login'

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    auth.error = null
    auth.isAuthenticated = false
  })

  it('validates the draft and submits credentials before reporting success', async () => {
    const onSuccess = vi.fn()
    auth.login.mockResolvedValue(undefined)
    render(<LoginForm onSuccess={onSuccess} onSwitchToRegister={vi.fn()} />)

    fireEvent.submit(screen.getByRole('button', { name: 'Login' }).closest('form')!)
    expect(await screen.findByText('Username is required')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'operator' } })
    expect(screen.queryByText('Username is required')).not.toBeInTheDocument()
    fireEvent.submit(screen.getByRole('button', { name: 'Login' }).closest('form')!)
    expect(await screen.findByText('Password is required')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    expect(screen.queryByText('Password is required')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))

    await waitFor(() => expect(auth.login).toHaveBeenCalledWith('operator', 'secret'))
    expect(onSuccess).toHaveBeenCalledOnce()
    expect(screen.getByLabelText('Username')).toHaveValue('')
  })

  it('keeps authentication failures visible', async () => {
    auth.login.mockRejectedValue(Object.assign(new Error('request failed'), {
      response: { status: 401, data: { detail: 'wrong credentials' } },
    }))
    render(<LoginForm onSuccess={undefined} onSwitchToRegister={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'operator' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))
    expect(await screen.findByText('wrong credentials')).toBeInTheDocument()
  })

  it('does not leak a failed login into the registration form', async () => {
    auth.login.mockImplementation(async () => {
      auth.error = 'wrong credentials'
      throw Object.assign(new Error('request failed'), {
        response: { status: 401, data: { detail: 'wrong credentials' } },
      })
    })
    render(<Login />)
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'operator' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))
    expect(await screen.findByText('wrong credentials')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Register here/ }))

    expect(screen.getByRole('heading', { name: 'Create account' })).toBeInTheDocument()
    expect(screen.queryByText('wrong credentials')).not.toBeInTheDocument()
  })
})

describe('PasswordChangeModal', () => {
  it('validates and sends the complete password change contract', async () => {
    const onHide = vi.fn()
    const onPasswordChange = vi.fn().mockResolvedValue(undefined)
    render(
      <PasswordChangeModal
        show
        onHide={onHide}
        onPasswordChange={onPasswordChange}
      />,
    )

    fireEvent.submit(screen.getByRole('button', { name: 'Change Password' }).closest('form')!)
    expect(await screen.findByText('Current password is required')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Current Password'), { target: { value: 'old-secret' } })
    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'newpass1' } })
    fireEvent.change(screen.getByLabelText('Confirm New Password'), { target: { value: 'newpass1' } })
    fireEvent.click(screen.getAllByRole('button', { name: 'Change Password' }).at(-1)!)

    await waitFor(() => expect(onPasswordChange).toHaveBeenCalledWith({
      currentPassword: 'old-secret',
      newPassword: 'newpass1',
      confirmPassword: 'newpass1',
    }))
    expect(onHide).toHaveBeenCalledOnce()
  })
})

describe('UserProfile', () => {
  beforeEach(() => vi.clearAllMocks())

  it('owns an email draft and only leaves edit mode after a successful update', async () => {
    auth.updateUser.mockResolvedValue(undefined)
    render(<UserProfile />)

    fireEvent.click(screen.getByRole('button', { name: 'Edit Profile' }))
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'new@example.test' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))

    await waitFor(() => expect(auth.updateUser).toHaveBeenCalledWith({ email: 'new@example.test' }))
    expect(await screen.findByText('Profile updated successfully!')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit Profile' })).toBeInTheDocument()
  })

  it('passes password changes through the auth boundary', async () => {
    auth.changePassword.mockResolvedValue(undefined)
    render(<UserProfile />)
    fireEvent.click(screen.getAllByRole('button', { name: 'Change Password' }).at(-1)!)
    fireEvent.change(screen.getByLabelText('Current Password'), { target: { value: 'old-secret' } })
    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'newpass1' } })
    fireEvent.change(screen.getByLabelText('Confirm New Password'), { target: { value: 'newpass1' } })
    fireEvent.click(screen.getAllByRole('button', { name: 'Change Password' }).at(-1)!)

    await waitFor(() => expect(auth.changePassword).toHaveBeenCalledWith('old-secret', 'newpass1'))
    expect(await screen.findByText('Password changed successfully!')).toBeInTheDocument()
  })
})
