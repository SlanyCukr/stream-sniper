import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import EditUserForm from '@/components/admin/users/EditUserForm'
import UserManagementModals from '@/components/admin/users/UserManagementModals'
import UserManagementTable from '@/components/admin/users/UserManagementTable'
import { USER_ROLES } from '@/lib/auth/roles'
import type { AdminUserDto } from '@/lib/api/users'

const user = {
  id: 7,
  username: 'operator',
  email: 'operator@example.test',
  role: USER_ROLES.ADMIN,
  isActive: true,
  createdAt: '2026-07-14T10:00:00Z',
}

describe('admin user controls', () => {
  it('wires role, activation, edit, delete, and self-delete protection through the real table', () => {
    const onEdit = vi.fn()
    const onActivationChange = vi.fn()
    const onDelete = vi.fn()
    const onRoleChange = vi.fn()
    render(
      <UserManagementTable
        users={[user, { ...user, id: 1, username: 'root' }]}
        authenticatedUser={{ id: 1 } as unknown as AdminUserDto}
        onEdit={onEdit}
        onActivationChange={onActivationChange}
        onDelete={onDelete}
        onRoleChange={onRoleChange}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Change role for operator' }))
    fireEvent.click(screen.getByRole('button', { name: 'User' }))
    expect(onRoleChange).toHaveBeenCalledWith(7, USER_ROLES.USER)

    fireEvent.click(screen.getByRole('button', { name: 'Deactivate operator' }))
    expect(onActivationChange).toHaveBeenCalledWith(7, false)
    fireEvent.click(screen.getByRole('button', { name: 'Edit operator' }))
    expect(onEdit).toHaveBeenCalledWith(user)
    fireEvent.click(screen.getByRole('button', { name: 'Delete operator' }))
    expect(onDelete).toHaveBeenCalledWith(user)
    expect(screen.getByRole('button', { name: 'Delete root' })).toBeDisabled()
  })

  it('submits edits and delete confirmation through the real modal controls', () => {
    const onClose = vi.fn()
    const onUpdate = vi.fn()
    const onDelete = vi.fn()
    const { rerender } = render(
      <UserManagementModals
        dialog={{ type: 'edit', user }}
        onClose={onClose}
        onUpdate={onUpdate}
        onDelete={onDelete}
      />,
    )

    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'new@example.test' } })
    fireEvent.change(screen.getByLabelText('Role'), { target: { value: USER_ROLES.USER } })
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))
    expect(onUpdate).toHaveBeenCalledWith({
      ...user,
      email: 'new@example.test',
      role: USER_ROLES.USER,
    })

    rerender(
      <UserManagementModals
        dialog={{ type: 'delete', user }}
        onClose={onClose}
        onUpdate={onUpdate}
        onDelete={onDelete}
      />,
    )
    expect(screen.getByText(/delete user "operator"/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Delete user' }))
    expect(onDelete).toHaveBeenCalledOnce()
  })

  it('keeps the standalone edit form contract usable without its modal shell', () => {
    const onSave = vi.fn()
    render(<EditUserForm user={user} onSave={onSave} onCancel={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))
    expect(onSave).toHaveBeenCalledWith(user)
  })
})
