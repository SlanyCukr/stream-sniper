'use client'
import {
    Table, ButtonGroup, Button, Dropdown,
} from 'react-bootstrap'

const UserManagementTable = ({
    users,
    authenticatedUser,
    handleEditUser,
    handleUserAction,
    handleDeleteUser,
    handleRoleChange,
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
                                    <Dropdown.Item
                                        onClick={() => handleRoleChange(userItem.id, 'user')}
                                        disabled={userItem.role === 'user'}
                                    >
                                        User
                                    </Dropdown.Item>
                                    <Dropdown.Item
                                        onClick={() => handleRoleChange(userItem.id, 'admin')}
                                        disabled={userItem.role === 'admin'}
                                    >
                                        Admin
                                    </Dropdown.Item>
                                </Dropdown.Menu>
                            </Dropdown>
                        </td>
                        <td>
                            <span className={userItem.is_active ? 'status-chip is-ok' : 'status-chip is-err'}>
                                {userItem.is_active ? 'Active' : 'Inactive'}
                            </span>
                        </td>
                        <td className="mono">{new Date(userItem.created_at).toLocaleDateString()}</td>
                        <td>
                            <ButtonGroup size="sm">
                                <Button
                                    variant="outline-primary"
                                    onClick={() => handleEditUser(userItem)}
                                    aria-label={`Edit ${userItem.username}`}
                                >
                                    <i
                                        className="bi bi-pencil"
                                        aria-hidden="true" />
                                </Button>
                                <Button
                                    variant="outline-primary"
                                    onClick={() => handleUserAction(userItem.id, userItem.is_active ? 'deactivate' : 'activate')}
                                    aria-label={`${userItem.is_active ? 'Deactivate' : 'Activate'} ${userItem.username}`}
                                >
                                    <i
                                        className={`bi bi-${userItem.is_active ? 'pause' : 'play'}`}
                                        aria-hidden="true" />
                                </Button>
                                <Button
                                    variant="outline-danger"
                                    onClick={() => handleDeleteUser(userItem)}
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
