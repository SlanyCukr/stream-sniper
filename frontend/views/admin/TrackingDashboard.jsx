'use client'

import TrackingDashboardContent from '@/components/admin/tracking/dashboard/TrackingDashboardContent'
import { useTrackingStats } from '@/hooks/admin/tracking/useTrackingQueries'
import QueryState from '@/components/common/QueryState'
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
            <QueryState
                query={query}
                errorTitle="Tracking statistics unavailable"
                showErrorDetails={false}
            >
                {data => (
                    <TrackingDashboardContent
                        stats={data}
                        onRefresh={query.refetch}
                        loading={query.isPending}
                    />
                )}
            </QueryState>
        </>
    )
}

export default TrackingDashboard
