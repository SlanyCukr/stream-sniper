import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import EditUserForm from '@/components/admin/users/EditUserForm'
import UserManagementModals from '@/components/admin/users/UserManagementModals'
import UserManagementTable from '@/components/admin/users/UserManagementTable'
import { USER_ROLES } from '@/lib/auth/roles'
import type { AuthUser } from '@/lib/auth/service'

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
        authenticatedUser={{ ...user, id: 1 } satisfies AuthUser}
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
    const onUpdate = vi.fn().mockResolvedValue(undefined)
    const onDelete = vi.fn().mockResolvedValue(undefined)
    const { rerender } = render(
      <UserManagementModals
        dialog={{ type: 'edit', user }}
        onClose={onClose}
        onUpdate={onUpdate}
        onDelete={onDelete}
        updatePending={false}
        deletePending={false}
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
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalledOnce()
    onClose.mockClear()

    rerender(
      <UserManagementModals
        dialog={{ type: 'delete', user }}
        onClose={onClose}
        onUpdate={onUpdate}
        onDelete={onDelete}
        updatePending={false}
        deletePending={false}
      />,
    )
    expect(screen.getByText(/delete user "operator"/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Delete user' }))
    expect(onDelete).toHaveBeenCalledWith(user.id)
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('keeps the standalone edit form contract usable without its modal shell', () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    render(<EditUserForm user={user} onSave={onSave} onCancel={vi.fn()} isPending={false} />)
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))
    expect(onSave).toHaveBeenCalledWith(user)
  })

  it('locks edit controls and dismissal while an update is pending', () => {
    const onClose = vi.fn()
    render(
      <UserManagementModals
        dialog={{ type: 'edit', user }}
        onClose={onClose}
        onUpdate={vi.fn().mockResolvedValue(undefined)}
        onDelete={vi.fn().mockResolvedValue(undefined)}
        updatePending
        deletePending={false}
      />,
    )

    expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeDisabled()
    expect(screen.getByLabelText('Role')).toBeDisabled()
    expect(screen.getByLabelText('Active')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Save Changes' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
  })

  it('locks delete controls and dismissal while deletion is pending', () => {
    const onClose = vi.fn()
    const onDelete = vi.fn().mockResolvedValue(undefined)
    render(
      <UserManagementModals
        dialog={{ type: 'delete', user }}
        onClose={onClose}
        onUpdate={vi.fn().mockResolvedValue(undefined)}
        onDelete={onDelete}
        updatePending={false}
        deletePending
      />,
    )

    expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Delete user' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Delete user' }))
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })
    expect(onDelete).not.toHaveBeenCalled()
    expect(onClose).not.toHaveBeenCalled()
  })

  it('renders no modal when no user action is selected', () => {
    render(
      <UserManagementModals
        dialog={null}
        onClose={vi.fn()}
        onUpdate={vi.fn().mockResolvedValue(undefined)}
        onDelete={vi.fn().mockResolvedValue(undefined)}
        updatePending={false}
        deletePending={false}
      />,
    )

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
