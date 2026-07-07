'use client'
import {
    Table, Badge, ButtonGroup, Button, Dropdown,
} from 'react-bootstrap'

const UserManagementTable = ({
    users,
    authenticatedUser,
    handleEditUser,
    handleUserAction,
    handleDeleteUser,
    handleRoleChange,
}) => (
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
                    <td>{userItem.id}</td>
                    <td>{userItem.username}</td>
                    <td>{userItem.email}</td>
                    <td>
                        <Dropdown>
                            <Dropdown.Toggle
                                variant={userItem.role === 'admin' ? 'warning' : 'secondary'}
                                size="sm"
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
                        <Badge bg={userItem.is_active ? 'success' : 'secondary'}>
                            {userItem.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                    </td>
                    <td>{new Date(userItem.created_at).toLocaleDateString()}</td>
                    <td>
                        <ButtonGroup size="sm">
                            <Button
                                variant="outline-primary"
                                onClick={() => handleEditUser(userItem)}
                            >
                                <i className="bi bi-pencil"></i>
                            </Button>
                            <Button
                                variant={userItem.is_active ? 'outline-warning' : 'outline-success'}
                                onClick={() => handleUserAction(userItem.id, userItem.is_active ? 'deactivate' : 'activate')}
                            >
                                <i className={`bi bi-${userItem.is_active ? 'pause' : 'play'}`}></i>
                            </Button>
                            <Button
                                variant="outline-danger"
                                onClick={() => handleDeleteUser(userItem)}
                                disabled={authenticatedUser.id === userItem.id} // Prevent admin from deleting themselves
                            >
                                <i className="bi bi-trash"></i>
                            </Button>
                        </ButtonGroup>
                    </td>
                </tr>
            ))}
        </tbody>
    </Table>
)

export default UserManagementTable
