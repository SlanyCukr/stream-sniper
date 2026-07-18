import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { USER_ROLES } from '@/lib/auth/roles'

const hooks = vi.hoisted(() => ({
  useAdminUsers: vi.fn(),
  useDeleteAdminUser: vi.fn(),
  useSetAdminUserActive: vi.fn(),
  useUpdateAdminUser: vi.fn(),
  useUpdateAdminUserRole: vi.fn(),
}))

vi.mock('@/hooks/admin/users/useUserAdminQueries', () => hooks)
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 1 } }) }))
vi.mock('@/components/admin/users/UserManagementModals', () => ({
  default: ({ dialog, onUpdate, onDelete }: {
    dialog: unknown
    onUpdate: CallableFunction
    onDelete: CallableFunction
  }) => (
    <>
      <button type="button" onClick={() => onUpdate({ id: 7, email: 'a@b.test', role: 'admin', isActive: true })}>
        update user
      </button>
      {dialog ? <span>dialog open</span> : null}
      {dialog ? <button type="button" onClick={() => onDelete()}>confirm delete</button> : null}
    </>
  ),
}))
vi.mock('@/components/admin/users/UserManagementTable', () => ({
  default: ({ onRoleChange, onActivationChange, onDelete }: {
    onRoleChange: CallableFunction
    onActivationChange: CallableFunction
    onDelete: CallableFunction
  }) => (
    <>
      <button type="button" onClick={() => onRoleChange(7, USER_ROLES.USER)}>
        change role
      </button>
      <button type="button" onClick={() => onActivationChange(7, false)}>
        deactivate user
      </button>
      <button type="button" onClick={() => onDelete({ id: 7 })}>
        delete user
      </button>
    </>
  ),
}))

import UserManagement from '@/views/admin/UserManagement'

describe('UserManagement action lifecycle', () => {
  const updateUser = { mutateAsync: vi.fn() }
  const updateRole = { mutateAsync: vi.fn() }
  const setUserActive = { mutateAsync: vi.fn() }
  const deleteUser = { mutateAsync: vi.fn() }

  beforeEach(() => {
    vi.clearAllMocks()
    hooks.useAdminUsers.mockReturnValue({
      data: { items: [{ id: 7 }], total: 1, pageCount: 1 },
      error: null,
      isPending: false,
      refetch: vi.fn(),
    })
    hooks.useUpdateAdminUser.mockReturnValue(updateUser)
    hooks.useUpdateAdminUserRole.mockReturnValue(updateRole)
    hooks.useDeleteAdminUser.mockReturnValue(deleteUser)
    hooks.useSetAdminUserActive.mockReturnValue(setUserActive)
  })

  it('shares success and normalized failure sequencing across user mutations', async () => {
    updateUser.mutateAsync.mockResolvedValue(undefined)
    updateRole.mutateAsync.mockRejectedValue({
      response: { status: 403, data: { detail: 'role forbidden' } },
      message: 'request failed',
    })
    render(<UserManagement />)

    fireEvent.click(screen.getByRole('button', { name: 'update user' }))
    await waitFor(() => expect(screen.getByText('User updated successfully')).toBeInTheDocument())
    expect(updateUser.mutateAsync).toHaveBeenCalledWith({
      userId: 7,
      changes: { email: 'a@b.test', role: 'admin', is_active: true },
    })

    fireEvent.click(screen.getByRole('button', { name: 'change role' }))
    await waitFor(() => expect(screen.getByText('role forbidden')).toBeInTheDocument())
    expect(screen.getByText('role forbidden').closest('.alert')).toHaveClass('alert-warning')
    expect(updateRole.mutateAsync).toHaveBeenCalledWith({ userId: 7, role: USER_ROLES.USER })

    setUserActive.mutateAsync.mockResolvedValue(undefined)
    fireEvent.click(screen.getByRole('button', { name: 'deactivate user' }))
    await waitFor(() => expect(setUserActive.mutateAsync).toHaveBeenCalledWith({
      userId: 7,
      isActive: false,
    }))
    expect(screen.getByText('User deactivated successfully')).toBeInTheDocument()
  })

  it('keeps a failed delete dialog open', async () => {
    deleteUser.mutateAsync.mockRejectedValue({ response: { status: 500, data: { detail: 'delete offline' } } })
    render(<UserManagement />)

    fireEvent.click(screen.getByRole('button', { name: 'delete user' }))
    fireEvent.click(screen.getByRole('button', { name: 'confirm delete' }))

    await waitFor(() => expect(screen.getByText('delete offline')).toBeInTheDocument())
    expect(screen.getByText('dialog open')).toBeInTheDocument()
  })

  it('moves back after deleting the last user on a page', async () => {
    const queryParams: Array<Record<string, unknown>> = []
    hooks.useAdminUsers.mockImplementation((params) => {
      queryParams.push(params)
      return {
        data: { items: [{ id: 7 }], total: 21, pageCount: 2 },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      }
    })
    deleteUser.mutateAsync.mockResolvedValue(undefined)
    render(<UserManagement />)

    fireEvent.click(screen.getByLabelText('Go to page 2'))
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 1 })
    fireEvent.click(screen.getByRole('button', { name: 'delete user' }))
    fireEvent.click(screen.getByRole('button', { name: 'confirm delete' }))

    await waitFor(() => expect(deleteUser.mutateAsync).toHaveBeenCalledWith(7))
    await waitFor(() => expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0 }))
    expect(screen.queryByText('dialog open')).not.toBeInTheDocument()
  })
})
