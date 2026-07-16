import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const auth = vi.hoisted(() => ({
  register: vi.fn(),
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    register: auth.register,
    isInitializing: false,
    error: null,
  }),
}))

import RegisterForm from '@/components/auth/register/RegisterForm'
import { expandThumbnailUrl } from '@/components/stream/list/thumbnailUrl'

const fillValidForm = () => {
  fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'operator' } })
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'operator@example.test' } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password1' } })
  fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'password1' } })
}

describe('RegisterForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('submits, resets its initial model, and calls success directly', async () => {
    const onSuccess = vi.fn()
    auth.register.mockResolvedValue(undefined)
    render(<RegisterForm onSuccess={onSuccess} onSwitchToLogin={undefined} />)
    fillValidForm()

    fireEvent.click(screen.getByRole('button', { name: 'Create Account' }))

    await waitFor(() => expect(auth.register).toHaveBeenCalledWith(
      'operator',
      'operator@example.test',
      'password1',
    ))
    expect(onSuccess).toHaveBeenCalledOnce()
    expect(screen.getByLabelText('Username')).toHaveValue('')
    expect(screen.getByLabelText('Email')).toHaveValue('')
  })

  it('renders the registration result error without clearing the draft', async () => {
    auth.register.mockRejectedValue(Object.assign(new Error('request failed'), {
      response: { status: 409, data: { detail: 'account exists' } },
    }))
    render(<RegisterForm onSuccess={undefined} onSwitchToLogin={undefined} />)
    fillValidForm()

    fireEvent.click(screen.getByRole('button', { name: 'Create Account' }))

    expect(await screen.findByText('account exists')).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toHaveValue('operator')
  })
})

describe('expandThumbnailUrl', () => {
  it('expands stream-owned dimensions and preserves missing thumbnails', () => {
    expect(expandThumbnailUrl('https://img/%{width}x%{height}.jpg', 320, 180))
      .toBe('https://img/320x180.jpg')
    expect(expandThumbnailUrl(null, 320, 180)).toBeNull()
  })
})
