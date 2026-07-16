import { useState } from 'react'
import { useActionFeedback } from '../shared/useActionFeedback'
import {
    useAdminUsers,
    useDeleteAdminUser,
    useSetAdminUserActive,
    useUpdateAdminUser,
    useUpdateAdminUserRole,
} from './useUserAdminQueries'

const PAGE_SIZE = 20

export const useUserManagementController = () => {
    const [dialog, setDialog] = useState(null)
    const [pageIndex, setPageIndex] = useState(0)
    const {
        data: usersData,
        error: usersError,
        isPending: loading,
        refetch: fetchUsers,
    } = useAdminUsers({
        pageIndex,
        pageSize: PAGE_SIZE,
    })
    const users = usersData?.items || []
    const totalUsers = usersData?.total || 0
    const pageCount = usersData?.pageCount || 0
    const feedback = useActionFeedback()
    const updateUser = useUpdateAdminUser()
    const deleteUser = useDeleteAdminUser()
    const setUserActive = useSetAdminUserActive()
    const updateUserRole = useUpdateAdminUserRole()

    const handleEditUser = user => setDialog({ type: 'edit', user })
    const handleDeleteUser = user => setDialog({ type: 'delete', user })

    const handleUserUpdate = updatedUser => feedback.runAction({
        action: () => updateUser.mutateAsync({
            userId: updatedUser.id,
            changes: {
                email: updatedUser.email,
                role: updatedUser.role,
                is_active: updatedUser.isActive,
            },
        }),
        successMessage: 'User updated successfully',
        errorTitle: 'Failed to update user',
        onSuccess: () => setDialog(null),
    })

    const handleUserDelete = () => feedback.runAction({
        action: () => deleteUser.mutateAsync(dialog.user.id),
        successMessage: 'User deleted successfully',
        errorTitle: 'Failed to delete user',
        onSuccess: () => {
            setDialog(null)
            if (users.length === 1) {
                setPageIndex(current => Math.max(current - 1, 0))
            }
        },
    })

    const handleActivationChange = (userId, isActive) => feedback.runAction({
        action: () => setUserActive.mutateAsync({
            userId,
            isActive,
        }),
        successMessage: `User ${isActive ? 'activated' : 'deactivated'} successfully`,
        errorTitle: `Failed to ${isActive ? 'activate' : 'deactivate'} user`,
    })

    const handleRoleChange = (userId, role) => feedback.runAction({
        action: () => updateUserRole.mutateAsync({
            userId,
            role,
        }),
        successMessage: 'User role updated successfully',
        errorTitle: 'Failed to update user role',
    })

    return {
        queryState: {
            error: usersError,
            isLoading: loading,
            refetch: fetchUsers,
        },
        tableProps: {
            users,
            onEdit: handleEditUser,
            onActivationChange: handleActivationChange,
            onDelete: handleDeleteUser,
            onRoleChange: handleRoleChange,
        },
        paginationProps: {
            pageIndex,
            pageSize: PAGE_SIZE,
            pageCount,
            total: totalUsers,
            onPageChange: setPageIndex,
        },
        modalProps: {
            dialog,
            onClose: () => setDialog(null),
            onUpdate: handleUserUpdate,
            onDelete: handleUserDelete,
        },
        feedback,
    }
}
