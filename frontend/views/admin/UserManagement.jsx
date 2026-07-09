'use client'
import { useState } from 'react'
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
import { getApiErrorMessage } from '@/lib/api'
import {
    useAdminUsers,
    useDeleteAdminUser,
    useSetAdminUserActive,
    useUpdateAdminUser,
    useUpdateAdminUserRole,
} from '@/hooks/useUserAdminQueries'

const UserManagement = () => {
    const { user: authenticatedUser } = useAuth()
    const [actionError, setActionError] = useState(null)
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
        usersPerPage,
    ] = useState(20)

    const {
        data: usersData,
        error: usersError,
        isPending: loading,
        refetch: fetchUsers,
    } = useAdminUsers({
        offset: (currentPage - 1) * usersPerPage,
        limit: usersPerPage,
    })
    const users = usersData?.users || []
    const totalUsers = usersData?.total || 0
    const error = actionError || (usersError && getApiErrorMessage(usersError, 'Failed to fetch users'))
    const updateUser = useUpdateAdminUser()
    const deleteUser = useDeleteAdminUser()
    const setUserActive = useSetAdminUserActive()
    const updateUserRole = useUpdateAdminUserRole()

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
            setActionError(null)
            await updateUser.mutateAsync({
                userId: updatedUser.id,
                changes: {
                    email: updatedUser.email,
                    role: updatedUser.role,
                    is_active: updatedUser.is_active,
                },
            })
            setSuccess('User updated successfully')
            setShowEditModal(false)
        } catch (updateError) {
            console.error('Error updating user:', updateError)
            setActionError(getApiErrorMessage(updateError, 'Failed to update user'))
        }
    }

    const handleUserDelete = async () => {
        try {
            setActionError(null)
            await deleteUser.mutateAsync(selectedUser.id)
            setSuccess('User deleted successfully')
            setShowDeleteModal(false)
        } catch (deleteError) {
            console.error('Error deleting user:', deleteError)
            setActionError(getApiErrorMessage(deleteError, 'Failed to delete user'))
        }
    }

    const handleUserAction = async (userId, action) => {
        try {
            setActionError(null)
            await setUserActive.mutateAsync({
                userId,
                isActive: action === 'activate',
            })
            setSuccess(`User ${action}d successfully`)
        } catch (actionError) {
            console.error(`Error ${action} user:`, actionError)
            setActionError(getApiErrorMessage(actionError, `Failed to ${action} user`))
        }
    }

    const handleRoleChange = async (userId, newRole) => {
        try {
            setActionError(null)
            await updateUserRole.mutateAsync({
                userId,
                role: newRole,
            })
            setSuccess('User role updated successfully')
        } catch (roleError) {
            console.error('Error updating user role:', roleError)
            setActionError(getApiErrorMessage(roleError, 'Failed to update user role'))
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
                    dismissible={Boolean(actionError)}
                    onClose={() => setActionError(null)}>
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
