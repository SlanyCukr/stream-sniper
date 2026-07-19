'use client'
import {
    Button,
} from 'react-bootstrap'
import ActionFeedback from '@/components/admin/ActionFeedback'
import SystemHealthOverview from '@/components/admin/system/SystemHealthOverview'
import ComponentsHealth from '@/components/admin/system/ComponentsHealth'
import RequestStatistics from '@/components/admin/system/RequestStatistics'
import RateLimitingMetrics from '@/components/admin/system/RateLimitingMetrics'
import CacheDetails from '@/components/admin/system/CacheDetails'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import StatusChip from '@/components/common/StatusChip'
import { useActionFeedback } from '@/hooks/admin/shared/useActionFeedback'
import { formatDurationDaysHoursMinutes } from '@/utils/numberUtils'
import {
    useCacheStats,
    useDetailedHealth,
    useFlushCache,
    useSystemMetrics,
} from '@/hooks/admin/system/useSystemQueries'

type StatusChipVariant = 'ok' | 'warn' | 'err' | 'neutral'

const SystemInfo = () => {
    const feedback = useActionFeedback()
    const healthQuery = useDetailedHealth()
    const metricsQuery = useSystemMetrics()
    const cacheStatsQuery = useCacheStats()
    const flushCacheMutation = useFlushCache()
    const healthData = healthQuery.data
    const metricsData = metricsQuery.data
    const cacheStats = cacheStatsQuery.data
    const hasTelemetry = Boolean(healthData || metricsData || cacheStats)
    const loading = !hasTelemetry && (
        healthQuery.isPending || metricsQuery.isPending || cacheStatsQuery.isPending
    )
    const refreshing = healthQuery.isFetching || metricsQuery.isFetching || cacheStatsQuery.isFetching
    const telemetryError = healthQuery.error || metricsQuery.error || cacheStatsQuery.error

    const fetchSystemInfo = async () => {
        await Promise.all([
            healthQuery.refetch(),
            metricsQuery.refetch(),
            cacheStatsQuery.refetch(),
        ])
    }

    const renderStatusBadge = (status: string) => {
        const statusVariants: Record<string, StatusChipVariant> = {
            'healthy': 'ok',
            'degraded': 'warn',
            'unhealthy': 'err',
            'critical': 'err',
        }
        return (
            <StatusChip variant={statusVariants[status] || 'neutral'}>
                {status}
            </StatusChip>
        )
    }

    const flushCache = () => feedback.runAction({
        action: () => flushCacheMutation.mutateAsync(),
        successMessage: 'Cache flushed successfully',
        errorTitle: 'Error flushing cache',
    })

    if (loading) {
        return <LoadingSpinner size="lg" text="Loading system telemetry..." />
    }

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">System information</h1>
                    <p className="page-sub">Health · metrics · monitoring</p>
                </div>
                <div className="page-actions">
                    <Button
                        variant="outline-primary"
                        onClick={fetchSystemInfo}
                        disabled={refreshing}>
                        <i className="bi bi-arrow-clockwise me-2"></i>
                        Refresh
                    </Button>
                </div>
            </div>

            <ErrorAlert
                error={telemetryError}
                title="System telemetry incomplete"
                onRetry={fetchSystemInfo}
                className="mb-4" />

            <ActionFeedback feedback={feedback} />

            {!hasTelemetry && (
                <div className="card">
                    <div className="empty-state">
                        <div
                            className="empty-scope"
                            aria-hidden="true" />
                        <p className="empty-title">Telemetry offline</p>
                        <p className="empty-hint">
                            None of the monitoring endpoints responded (health, metrics, cache).
                            The API may be up while its metrics backend is down — try Refresh, and
                            check the api container logs if this persists.
                        </p>
                    </div>
                </div>
            )}

            {healthData && (
                <SystemHealthOverview
                    healthData={healthData}
                    formatUptime={formatDurationDaysHoursMinutes}
                    renderStatusBadge={renderStatusBadge}
                />
            )}

            {healthData && healthData.components.length > 0 && (
                <ComponentsHealth
                    components={healthData.components}
                    renderStatusBadge={renderStatusBadge} />
            )}

            {metricsData?.requests && (
                <RequestStatistics
                    requests={metricsData.requests}
                    cache={metricsData.cache}
                    flushCache={flushCache}
                />
            )}

            {metricsData?.rateLimiting && (
                <RateLimitingMetrics rateLimiting={metricsData.rateLimiting} />
            )}

            {cacheStats && (
                <CacheDetails cacheStats={cacheStats} />
            )}
        </>
    )
}

export default SystemInfo
