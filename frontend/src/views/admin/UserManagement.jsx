import React, { useState, useEffect } from 'react';
import { 
    Container, 
    Row, 
    Col, 
    Card, 
    Table, 
    Button, 
    Alert, 
    Spinner, 
    Badge,
    Modal,
    Form,
    Pagination,
    ButtonGroup,
    Dropdown
} from 'react-bootstrap';
import { useAuth } from '../../contexts/AuthContext';
import env from 'react-dotenv';

const UserManagement = () => {
    const { user, token } = useAuth();
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [selectedUser, setSelectedUser] = useState(null);
    const [showEditModal, setShowEditModal] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalUsers, setTotalUsers] = useState(0);
    const [usersPerPage] = useState(20);

    useEffect(() => {
        fetchUsers();
    }, [currentPage]);

    const fetchUsers = async () => {
        try {
            setLoading(true);
            setError(null);
            
            const offset = (currentPage - 1) * usersPerPage;
            const response = await fetch(`${env.API_URL}/auth/users?offset=${offset}&limit=${usersPerPage}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                setUsers(data.users);
                setTotalUsers(data.total);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch users');
            }
        } catch (error) {
            console.error('Error fetching users:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleEditUser = (userToEdit) => {
        setSelectedUser(userToEdit);
        setShowEditModal(true);
    };

    const handleDeleteUser = (userToDelete) => {
        setSelectedUser(userToDelete);
        setShowDeleteModal(true);
    };

    const handleUserUpdate = async (updatedUser) => {
        try {
            const response = await fetch(`${env.API_URL}/auth/users/${updatedUser.id}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: updatedUser.email,
                    role: updatedUser.role,
                    is_active: updatedUser.is_active
                })
            });

            if (response.ok) {
                setSuccess('User updated successfully');
                setShowEditModal(false);
                fetchUsers();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to update user');
            }
        } catch (error) {
            console.error('Error updating user:', error);
            setError(error.message);
        }
    };

    const handleUserDelete = async () => {
        try {
            const response = await fetch(`${env.API_URL}/auth/users/${selectedUser.id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                setSuccess('User deleted successfully');
                setShowDeleteModal(false);
                fetchUsers();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to delete user');
            }
        } catch (error) {
            console.error('Error deleting user:', error);
            setError(error.message);
        }
    };

    const handleUserAction = async (userId, action) => {
        try {
            const endpoint = action === 'activate' ? 'activate' : 'deactivate';
            const response = await fetch(`${env.API_URL}/auth/users/${userId}/${endpoint}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                setSuccess(`User ${action}d successfully`);
                fetchUsers();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Failed to ${action} user`);
            }
        } catch (error) {
            console.error(`Error ${action} user:`, error);
            setError(error.message);
        }
    };

    const handleRoleChange = async (userId, newRole) => {
        try {
            const response = await fetch(`${env.API_URL}/auth/users/${userId}/role`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ role: newRole })
            });

            if (response.ok) {
                setSuccess('User role updated successfully');
                fetchUsers();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to update user role');
            }
        } catch (error) {
            console.error('Error updating user role:', error);
            setError(error.message);
        }
    };

    const totalPages = Math.ceil(totalUsers / usersPerPage);

    const renderPagination = () => {
        const items = [];
        const maxPagesToShow = 5;
        
        let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
        let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
        
        if (endPage - startPage + 1 < maxPagesToShow) {
            startPage = Math.max(1, endPage - maxPagesToShow + 1);
        }

        for (let page = startPage; page <= endPage; page++) {
            items.push(
                <Pagination.Item
                    key={page}
                    active={page === currentPage}
                    onClick={() => setCurrentPage(page)}
                >
                    {page}
                </Pagination.Item>
            );
        }

        return (
            <Pagination>
                <Pagination.First onClick={() => setCurrentPage(1)} disabled={currentPage === 1} />
                <Pagination.Prev onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage === 1} />
                {items}
                <Pagination.Next onClick={() => setCurrentPage(currentPage + 1)} disabled={currentPage === totalPages} />
                <Pagination.Last onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages} />
            </Pagination>
        );
    };

    if (loading) {
        return (
            <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '300px' }}>
                <Spinner animation="border" variant="primary" />
            </Container>
        );
    }

    return (
        <Container>
            <Row className="mb-4">
                <Col>
                    <h2>User Management</h2>
                    <p className="text-muted">Manage user accounts and permissions</p>
                </Col>
                <Col xs="auto">
                    <Button variant="success" href="/admin/users/create">
                        <i className="bi bi-person-plus me-2"></i>
                        Create New User
                    </Button>
                </Col>
            </Row>

            {error && (
                <Alert variant="danger" dismissible onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {success && (
                <Alert variant="success" dismissible onClose={() => setSuccess(null)}>
                    {success}
                </Alert>
            )}

            <Card>
                <Card.Header className="d-flex justify-content-between align-items-center">
                    <h5 className="mb-0">Users ({totalUsers})</h5>
                    <Button variant="outline-primary" size="sm" onClick={fetchUsers}>
                        <i className="bi bi-arrow-clockwise"></i> Refresh
                    </Button>
                </Card.Header>
                <Card.Body>
                    <Table responsive hover>
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
                            {users.map(user => (
                                <tr key={user.id}>
                                    <td>{user.id}</td>
                                    <td>{user.username}</td>
                                    <td>{user.email}</td>
                                    <td>
                                        <Dropdown>
                                            <Dropdown.Toggle 
                                                variant={user.role === 'admin' ? 'warning' : 'secondary'}
                                                size="sm"
                                            >
                                                {user.role}
                                            </Dropdown.Toggle>
                                            <Dropdown.Menu>
                                                <Dropdown.Item 
                                                    onClick={() => handleRoleChange(user.id, 'user')}
                                                    disabled={user.role === 'user'}
                                                >
                                                    User
                                                </Dropdown.Item>
                                                <Dropdown.Item 
                                                    onClick={() => handleRoleChange(user.id, 'admin')}
                                                    disabled={user.role === 'admin'}
                                                >
                                                    Admin
                                                </Dropdown.Item>
                                            </Dropdown.Menu>
                                        </Dropdown>
                                    </td>
                                    <td>
                                        <Badge bg={user.is_active ? 'success' : 'secondary'}>
                                            {user.is_active ? 'Active' : 'Inactive'}
                                        </Badge>
                                    </td>
                                    <td>{new Date(user.created_at).toLocaleDateString()}</td>
                                    <td>
                                        <ButtonGroup size="sm">
                                            <Button 
                                                variant="outline-primary" 
                                                onClick={() => handleEditUser(user)}
                                            >
                                                <i className="bi bi-pencil"></i>
                                            </Button>
                                            <Button 
                                                variant={user.is_active ? 'outline-warning' : 'outline-success'}
                                                onClick={() => handleUserAction(user.id, user.is_active ? 'deactivate' : 'activate')}
                                            >
                                                <i className={`bi bi-${user.is_active ? 'pause' : 'play'}`}></i>
                                            </Button>
                                            <Button 
                                                variant="outline-danger" 
                                                onClick={() => handleDeleteUser(user)}
                                                disabled={user.id === user.id} // Prevent admin from deleting themselves
                                            >
                                                <i className="bi bi-trash"></i>
                                            </Button>
                                        </ButtonGroup>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                </Card.Body>
                <Card.Footer>
                    <div className="d-flex justify-content-between align-items-center">
                        <span>
                            Showing {((currentPage - 1) * usersPerPage) + 1} to {Math.min(currentPage * usersPerPage, totalUsers)} of {totalUsers} users
                        </span>
                        {renderPagination()}
                    </div>
                </Card.Footer>
            </Card>

            {/* Edit User Modal */}
            <Modal show={showEditModal} onHide={() => setShowEditModal(false)}>
                <Modal.Header closeButton>
                    <Modal.Title>Edit User</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    {selectedUser && (
                        <EditUserForm 
                            user={selectedUser} 
                            onSave={handleUserUpdate} 
                            onCancel={() => setShowEditModal(false)}
                        />
                    )}
                </Modal.Body>
            </Modal>

            {/* Delete Confirmation Modal */}
            <Modal show={showDeleteModal} onHide={() => setShowDeleteModal(false)}>
                <Modal.Header closeButton>
                    <Modal.Title>Confirm Delete</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    Are you sure you want to delete user "{selectedUser?.username}"? This action cannot be undone.
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
                        Cancel
                    </Button>
                    <Button variant="danger" onClick={handleUserDelete}>
                        Delete User
                    </Button>
                </Modal.Footer>
            </Modal>
        </Container>
    );
};

const EditUserForm = ({ user, onSave, onCancel }) => {
    const [formData, setFormData] = useState({
        email: user.email,
        role: user.role,
        is_active: user.is_active
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave({ ...user, ...formData });
    };

    return (
        <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
                <Form.Label>Email</Form.Label>
                <Form.Control
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                />
            </Form.Group>
            <Form.Group className="mb-3">
                <Form.Label>Role</Form.Label>
                <Form.Select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                </Form.Select>
            </Form.Group>
            <Form.Group className="mb-3">
                <Form.Check
                    type="checkbox"
                    label="Active"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
            </Form.Group>
            <div className="d-flex justify-content-end">
                <Button variant="secondary" onClick={onCancel} className="me-2">
                    Cancel
                </Button>
                <Button variant="primary" type="submit">
                    Save Changes
                </Button>
            </div>
        </Form>
    );
};

export default UserManagement;