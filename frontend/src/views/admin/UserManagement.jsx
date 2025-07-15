import {
    useState, useEffect, useCallback,
} from 'react'
import {
    Container,
    Row,
    Col,
    Card,
    Button,
    Alert,
    Spinner,
} from 'react-bootstrap'
import { useAuth } from '../../contexts/AuthContext'
import UserManagementTable from '../../components/admin/UserManagementTable'
import UserManagementModals from '../../components/admin/UserManagementModals'
import { renderPagination } from '../../utils/paginationUtils'

// Use environment variable from build time, fallback to /api for production
const API_URL = process.env.REACT_APP_API_URL || '/api'

const UserManagement = () => {
    const {
        user: authenticatedUser, token,
    } = useAuth()
    const [
        users,
        setUsers,
    ] = useState([
    ])
    const [
        loading,
        setLoading,
    ] = useState(true)
    const [
        error,
        setError,
    ] = useState(null)
    const [
        success,
        setSuccess,
    ] = useState(null)
    const [
        selectedUser,
        setSelectedUser,
    ] = useState(null)
    const [
        showEditModal,
        setShowEditModal,
    ] = useState(false)
    const [
        showDeleteModal,
        setShowDeleteModal,
    ] = useState(false)
    const [
        currentPage,
        setCurrentPage,
    ] = useState(1)
    const [
        totalUsers,
        setTotalUsers,
    ] = useState(0)
    const [
        usersPerPage,
    ] = useState(20)

    const fetchUsers = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            const offset = (currentPage - 1) * usersPerPage
            const response = await fetch(`${API_URL}/auth/users?offset=${offset}&limit=${usersPerPage}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            })

            if (response.ok) {
                const data = await response.json()
                setUsers(data.users)
                setTotalUsers(data.total)
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Failed to fetch users')
            }
        } catch (fetchError) {
            console.error('Error fetching users:', fetchError)
            setError(fetchError.message)
        } finally {
            setLoading(false)
        }
    }, [
        currentPage,
        usersPerPage,
        token,
    ])

    useEffect(() => {
        fetchUsers()
    }, [
        fetchUsers,
    ])

    const handleEditUser = userToEdit => {
        setSelectedUser(userToEdit)
        setShowEditModal(true)
    }

    const handleDeleteUser = userToDelete => {
        setSelectedUser(userToDelete)
        setShowDeleteModal(true)
    }

    const handleUserUpdate = async updatedUser => {
        try {
            const response = await fetch(`${API_URL}/auth/users/${updatedUser.id}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: updatedUser.email,
                    role: updatedUser.role,
                    is_active: updatedUser.is_active,
                }),
            })

            if (response.ok) {
                setSuccess('User updated successfully')
                setShowEditModal(false)
                fetchUsers()
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Failed to update user')
            }
        } catch (updateError) {
            console.error('Error updating user:', updateError)
            setError(updateError.message)
        }
    }

    const handleUserDelete = async () => {
        try {
            const response = await fetch(`${API_URL}/auth/users/${selectedUser.id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            })

            if (response.ok) {
                setSuccess('User deleted successfully')
                setShowDeleteModal(false)
                fetchUsers()
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Failed to delete user')
            }
        } catch (deleteError) {
            console.error('Error deleting user:', deleteError)
            setError(deleteError.message)
        }
    }

    const handleUserAction = async (userId, action) => {
        try {
            const endpoint = action === 'activate' ? 'activate' : 'deactivate'
            const response = await fetch(`${API_URL}/auth/users/${userId}/${endpoint}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            })

            if (response.ok) {
                setSuccess(`User ${action}d successfully`)
                fetchUsers()
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || `Failed to ${action} user`)
            }
        } catch (actionError) {
            console.error(`Error ${action} user:`, actionError)
            setError(actionError.message)
        }
    }

    const handleRoleChange = async (userId, newRole) => {
        try {
            const response = await fetch(`${API_URL}/auth/users/${userId}/role`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ role: newRole }),
            })

            if (response.ok) {
                setSuccess('User role updated successfully')
                fetchUsers()
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Failed to update user role')
            }
        } catch (roleError) {
            console.error('Error updating user role:', roleError)
            setError(roleError.message)
        }
    }

    const totalPages = Math.ceil(totalUsers / usersPerPage)


    if (loading) {
        return (
            <Container
                className="d-flex justify-content-center align-items-center"
                style={{ minHeight: '300px' }}>
                <Spinner
                    animation="border"
                    variant="primary" />
            </Container>
        )
    }

    return (
        <Container>
            <Row className="mb-4">
                <Col>
                    <h2>User Management</h2>
                    <p className="text-muted">Manage user accounts and permissions</p>
                </Col>
                <Col xs="auto">
                    <Button
                        variant="success"
                        href="/admin/users/create">
                        <i className="bi bi-person-plus me-2"></i>
                        Create New User
                    </Button>
                </Col>
            </Row>

            {error && (
                <Alert
                    variant="danger"
                    dismissible
                    onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {success && (
                <Alert
                    variant="success"
                    dismissible
                    onClose={() => setSuccess(null)}>
                    {success}
                </Alert>
            )}

            <Card>
                <Card.Header className="d-flex justify-content-between align-items-center">
                    <h5 className="mb-0">Users ({totalUsers})</h5>
                    <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={fetchUsers}>
                        <i className="bi bi-arrow-clockwise"></i> Refresh
                    </Button>
                </Card.Header>
                <Card.Body>
                    <UserManagementTable
                        users={users}
                        authenticatedUser={authenticatedUser}
                        handleEditUser={handleEditUser}
                        handleUserAction={handleUserAction}
                        handleDeleteUser={handleDeleteUser}
                        handleRoleChange={handleRoleChange}
                    />
                </Card.Body>
                <Card.Footer>
                    <div className="d-flex justify-content-between align-items-center">
                        <span>
                            Showing {((currentPage - 1) * usersPerPage) + 1} to {Math.min(currentPage * usersPerPage, totalUsers)} of {totalUsers} users
                        </span>
                        {renderPagination(currentPage, totalPages, setCurrentPage)}
                    </div>
                </Card.Footer>
            </Card>

            <UserManagementModals
                showEditModal={showEditModal}
                setShowEditModal={setShowEditModal}
                showDeleteModal={showDeleteModal}
                setShowDeleteModal={setShowDeleteModal}
                selectedUser={selectedUser}
                handleUserUpdate={handleUserUpdate}
                handleUserDelete={handleUserDelete}
            />
        </Container>
    )
}


export default UserManagement
