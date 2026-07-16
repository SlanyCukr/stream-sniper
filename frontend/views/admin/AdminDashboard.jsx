'use client'

import { useAuth } from '@/contexts/AuthContext'
import { useAdminSystemStats } from '@/hooks/admin/users/useUserAdminQueries'
import AdminQuickActions from '@/components/admin/dashboard/AdminQuickActions'
import AdminStatsGrid from '@/components/admin/dashboard/AdminStatsGrid'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const AdminDashboard = () => {
    const { user } = useAuth()
    const query = useAdminSystemStats()

    if (query.isPending) return <LoadingSpinner size="lg" text="Loading admin dashboard..." />

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Admin dashboard</h1>
                    <p className="page-sub">Welcome back, {user?.username}</p>
                </div>
            </div>
            <ErrorAlert
                error={query.error}
                title="Admin statistics unavailable"
                onRetry={query.refetch}
                className="mb-4"
            />
            {query.data ? <AdminStatsGrid stats={query.data} /> : null}
            <AdminQuickActions />
        </>
    )
}

export default AdminDashboard
