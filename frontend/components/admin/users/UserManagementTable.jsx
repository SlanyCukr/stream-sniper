'use client'
import {
    Table, ButtonGroup, Button, Dropdown,
} from 'react-bootstrap'
import { USER_ROLE_OPTIONS } from '@/lib/auth/roles'
import StatusChip from '@/components/common/StatusChip'

const UserManagementTable = ({
    users,
    authenticatedUser,
    onEdit,
    onActivationChange,
    onDelete,
    onRoleChange,
}) => {
    if (users.length === 0) {
        return (
            <div className="empty-state">
                <div
                    className="empty-scope"
                    aria-hidden="true" />
                <p className="empty-title">No users</p>
                <p className="empty-hint">No accounts match the current page — create one to get started.</p>
            </div>
        )
    }

    return (
        <Table
            responsive
            hover>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {users.map(userItem => (
                    <tr key={userItem.id}>
                        <td className="mono">{userItem.id}</td>
                        <td>{userItem.username}</td>
                        <td>{userItem.email}</td>
                        <td>
                            <Dropdown>
                                <Dropdown.Toggle
                                    variant="outline-primary"
                                    size="sm"
                                    aria-label={`Change role for ${userItem.username}`}
                                >
                                    {userItem.role}
                                </Dropdown.Toggle>
                                <Dropdown.Menu>
                                    {USER_ROLE_OPTIONS.map(option => (
                                        <Dropdown.Item
                                            key={option.value}
                                            onClick={() => onRoleChange(userItem.id, option.value)}
                                            disabled={userItem.role === option.value}
                                        >
                                            {option.label}
                                        </Dropdown.Item>
                                    ))}
                                </Dropdown.Menu>
                            </Dropdown>
                        </td>
                        <td>
                            <StatusChip variant={userItem.isActive ? 'ok' : 'err'}>
                                {userItem.isActive ? 'Active' : 'Inactive'}
                            </StatusChip>
                        </td>
                        <td className="mono">{new Date(userItem.createdAt).toLocaleDateString()}</td>
                        <td>
                            <ButtonGroup size="sm">
                                <Button
                                    variant="outline-primary"
                                    onClick={() => onEdit(userItem)}
                                    aria-label={`Edit ${userItem.username}`}
                                >
                                    <i
                                        className="bi bi-pencil"
                                        aria-hidden="true" />
                                </Button>
                                <Button
                                    variant="outline-primary"
                                    onClick={() => onActivationChange(userItem.id, !userItem.isActive)}
                                    aria-label={`${userItem.isActive ? 'Deactivate' : 'Activate'} ${userItem.username}`}
                                >
                                    <i
                                        className={`bi bi-${userItem.isActive ? 'pause' : 'play'}`}
                                        aria-hidden="true" />
                                </Button>
                                <Button
                                    variant="outline-danger"
                                    onClick={() => onDelete(userItem)}
                                    disabled={authenticatedUser.id === userItem.id} // Prevent admin from deleting themselves
                                    aria-label={`Delete ${userItem.username}`}
                                >
                                    <i
                                        className="bi bi-trash"
                                        aria-hidden="true" />
                                </Button>
                            </ButtonGroup>
                        </td>
                    </tr>
                ))}
            </tbody>
        </Table>
    )
}

export default UserManagementTable
