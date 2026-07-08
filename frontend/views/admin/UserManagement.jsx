'use client'
import {
    useState, useEffect, useCallback,
} from 'react'
import {
    Container,
    Card,
    Button,
    Alert,
    Spinner,
} from 'react-bootstrap'
import { useAuth } from '@/contexts/AuthContext'
import UserManagementTable from '@/components/admin/UserManagementTable'
import UserManagementModals from '@/components/admin/UserManagementModals'
import { renderPagination } from '@/utils/paginationUtils'
import { api } from '@/lib/api'

const UserManagement = () => {
    const { user: authenticatedUser } = useAuth()
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
            const { data } = await api.get(`/auth/users?offset=${offset}&limit=${usersPerPage}`)
            setUsers(data.users)
            setTotalUsers(data.total)
        } catch (fetchError) {
            console.error('Error fetching users:', fetchError)
            setError(fetchError.response?.data?.detail || fetchError.message || 'Failed to fetch users')
        } finally {
            setLoading(false)
        }
    }, [
        currentPage,
        usersPerPage,
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
            await api.put(`/auth/users/${updatedUser.id}`, {
                email: updatedUser.email,
                role: updatedUser.role,
                is_active: updatedUser.is_active,
            })
            setSuccess('User updated successfully')
            setShowEditModal(false)
            fetchUsers()
        } catch (updateError) {
            console.error('Error updating user:', updateError)
            setError(updateError.response?.data?.detail || updateError.message || 'Failed to update user')
        }
    }

    const handleUserDelete = async () => {
        try {
            await api.delete(`/auth/users/${selectedUser.id}`)
            setSuccess('User deleted successfully')
            setShowDeleteModal(false)
            fetchUsers()
        } catch (deleteError) {
            console.error('Error deleting user:', deleteError)
            setError(deleteError.response?.data?.detail || deleteError.message || 'Failed to delete user')
        }
    }

    const handleUserAction = async (userId, action) => {
        try {
            const endpoint = action === 'activate' ? 'activate' : 'deactivate'
            await api.put(`/auth/users/${userId}/${endpoint}`)
            setSuccess(`User ${action}d successfully`)
            fetchUsers()
        } catch (actionError) {
            console.error(`Error ${action} user:`, actionError)
            setError(actionError.response?.data?.detail || actionError.message || `Failed to ${action} user`)
        }
    }

    const handleRoleChange = async (userId, newRole) => {
        try {
            await api.put(`/auth/users/${userId}/role`, { role: newRole })
            setSuccess('User role updated successfully')
            fetchUsers()
        } catch (roleError) {
            console.error('Error updating user role:', roleError)
            setError(roleError.response?.data?.detail || roleError.message || 'Failed to update user role')
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
            <div className="page-head">
                <div>
                    <h1 className="page-title">User management</h1>
                    <p className="page-sub">Accounts &amp; permissions</p>
                </div>
                <div className="page-actions">
                    <Button
                        variant="primary"
                        href="/admin/users/create">
                        <i
                            className="bi bi-person-plus me-2"
                            aria-hidden="true" />
                        Create user
                    </Button>
                </div>
            </div>

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
                <Card.Body>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                        <h3 className="section-label mb-0">
                            Users <span className="mono">({totalUsers})</span>
                        </h3>
                        <Button
                            variant="outline-primary"
                            size="sm"
                            onClick={fetchUsers}>
                            <i
                                className="bi bi-arrow-clockwise me-2"
                                aria-hidden="true" />
                            Refresh
                        </Button>
                    </div>
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
                        <span className="mono small text-muted">
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
