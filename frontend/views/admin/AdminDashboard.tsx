'use client'

import { useAuth } from '@/contexts/AuthContext'
import { useAdminSystemStats } from '@/hooks/admin/users/useUserAdminQueries'
import AdminQuickActions from '@/components/admin/dashboard/AdminQuickActions'
import AdminStatsGrid from '@/components/admin/dashboard/AdminStatsGrid'
import QueryState from '@/components/common/QueryState'
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
            <QueryState
                query={query}
                errorTitle="Admin statistics unavailable"
                showErrorDetails={false}
            >
                {data => <AdminStatsGrid stats={data} />}
            </QueryState>
            <AdminQuickActions />
        </>
    )
}

export default AdminDashboard
