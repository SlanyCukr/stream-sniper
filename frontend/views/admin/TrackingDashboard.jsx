'use client'

import TrackingDashboardContent from '@/components/admin/tracking/dashboard/TrackingDashboardContent'
import { useTrackingStats } from '@/hooks/admin/tracking/useTrackingQueries'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const TrackingDashboard = () => {
    const query = useTrackingStats({ refetchInterval: 30000 })

    if (query.isPending && !query.data) {
        return <LoadingSpinner size="lg" text="Loading tracking statistics..." />
    }

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Tracking dashboard</h1>
                    <p className="page-sub">Automated stream tracking · processing system</p>
                </div>
                {query.data && query.dataUpdatedAt ? (
                    <div className="page-actions">
                        <span className="mono small text-muted">
                            Last updated: {new Date(query.dataUpdatedAt).toLocaleTimeString()}
                        </span>
                    </div>
                ) : null}
            </div>
            <ErrorAlert
                error={query.error}
                title="Tracking statistics unavailable"
                onRetry={query.refetch}
                className="mb-4" />
            {query.data ? (
                <TrackingDashboardContent
                    stats={query.data}
                    onRefresh={query.refetch}
                    loading={query.isPending}
                />
            ) : null}
        </>
    )
}

export default TrackingDashboard
