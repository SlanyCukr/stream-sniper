'use client'
import {
    Card,
    Button,
} from 'react-bootstrap'
import { useAuth } from '@/contexts/AuthContext'
import ActionFeedback from '@/components/admin/ActionFeedback'
import UserManagementTable from '@/components/admin/users/UserManagementTable'
import UserManagementModals from '@/components/admin/users/UserManagementModals'
import Pagination from '@/components/common/pagination/Pagination'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import { useUserManagementController } from '@/hooks/admin/users/useUserManagementController'

const UserManagement = () => {
    const { user: authenticatedUser } = useAuth()
    const {
        queryState,
        tableProps,
        paginationProps,
        modalProps,
        feedback,
    } = useUserManagementController()
    const {
        pageIndex, pageSize, pageCount, total, onPageChange,
    } = paginationProps

    if (queryState.isLoading) {
        return <LoadingSpinner size="lg" text="Loading users..." />
    }

    return (
        <>
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

            <ErrorAlert
                error={queryState.error}
                title="User accounts unavailable"
                onRetry={queryState.refetch}
                className="mb-4" />

            <ActionFeedback feedback={feedback} />

            <Card>
                <Card.Body>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                        <h3 className="section-label mb-0">
                            Users <span className="mono">({total})</span>
                        </h3>
                        <Button
                            variant="outline-primary"
                            size="sm"
                            onClick={() => queryState.refetch()}>
                            <i
                                className="bi bi-arrow-clockwise me-2"
                                aria-hidden="true" />
                            Refresh
                        </Button>
                    </div>
                    <UserManagementTable
                        {...tableProps}
                        authenticatedUser={authenticatedUser}
                    />
                </Card.Body>
                <Card.Footer>
                    <div className="d-flex justify-content-between align-items-center">
                        <span className="mono small text-muted">
                            Showing {total === 0 ? 0 : pageIndex * pageSize + 1} to {Math.min((pageIndex + 1) * pageSize, total)} of {total} users
                        </span>
                        <Pagination
                            pageIndex={pageIndex}
                            pageCount={pageCount}
                            onPageChange={onPageChange}
                            ariaLabel="User management pagination"
                        />
                    </div>
                </Card.Footer>
            </Card>

            <UserManagementModals {...modalProps} />
        </>
    )
}


export default UserManagement
