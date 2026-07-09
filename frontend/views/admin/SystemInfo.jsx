'use client'
import { useState } from 'react'
import {
    Container,
    Alert,
    Spinner,
    Button,
} from 'react-bootstrap'
import SystemHealthOverview from '@/components/admin/SystemHealthOverview'
import ComponentsHealth from '@/components/admin/ComponentsHealth'
import RequestStatistics from '@/components/admin/RequestStatistics'
import RateLimitingMetrics from '@/components/admin/RateLimitingMetrics'
import CacheDetails from '@/components/admin/CacheDetails'
import { getApiErrorMessage } from '@/lib/api'
import {
    useCacheStats,
    useDetailedHealth,
    useFlushCache,
    useSystemMetrics,
} from '@/hooks/useSystemQueries'


const SystemInfo = () => {
    const [actionError, setActionError] = useState(null)
    const [
        success,
        setSuccess,
    ] = useState(null)
    const healthQuery = useDetailedHealth()
    const metricsQuery = useSystemMetrics()
    const cacheStatsQuery = useCacheStats()
    const flushCacheMutation = useFlushCache()
    const healthData = healthQuery.data
    const metricsData = metricsQuery.data
    const cacheStats = cacheStatsQuery.data
    const loading = healthQuery.isPending || metricsQuery.isPending || cacheStatsQuery.isPending
    const refreshing = healthQuery.isFetching || metricsQuery.isFetching || cacheStatsQuery.isFetching
    const telemetryError = !healthData && !metricsData && !cacheStats && (
        healthQuery.error || metricsQuery.error || cacheStatsQuery.error
    )
    const error = actionError || telemetryError

    const fetchSystemInfo = async () => {
        setActionError(null)
        await Promise.all([
            healthQuery.refetch(),
            metricsQuery.refetch(),
            cacheStatsQuery.refetch(),
        ])
    }

    const formatUptime = seconds => {
        const days = Math.floor(seconds / 86400)
        const hours = Math.floor((seconds % 86400) / 3600)
        const minutes = Math.floor((seconds % 3600) / 60)

        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`
        } else {
            return `${minutes}m`
        }
    }

    const getStatusBadge = status => {
        const statusMap = {
            'healthy': 'is-ok',
            'degraded': 'is-warn',
            'unhealthy': 'is-err',
            'critical': 'is-err',
        }
        const modifier = statusMap[status]
        return (
            <span className={modifier ? `status-chip ${modifier}` : 'status-chip'}>
                {status}
            </span>
        )
    }

    const flushCache = async () => {
        setActionError(null)
        setSuccess(null)
        try {
            await flushCacheMutation.mutateAsync()
            setSuccess('Cache flushed successfully')
        } catch (flushError) {
            console.error('Error flushing cache:', flushError)
            setActionError(getApiErrorMessage(flushError, 'Error flushing cache'))
        }
    }

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

            {error && (
                <Alert
                    variant="danger"
                    className="mb-4"
                    dismissible={Boolean(actionError)}
                    onClose={() => setActionError(null)}>
                    {getApiErrorMessage(error, 'Unable to fetch system telemetry')}
                </Alert>
            )}

            {success && (
                <Alert
                    variant="success"
                    className="mb-4"
                    dismissible
                    onClose={() => setSuccess(null)}>
                    {success}
                </Alert>
            )}

            {!healthData && !metricsData && !cacheStats && (
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
                    formatUptime={formatUptime}
                    getStatusBadge={getStatusBadge}
                />
            )}

            {healthData?.components && (
                <ComponentsHealth
                    healthData={healthData}
                    getStatusBadge={getStatusBadge} />
            )}

            {/* Request Metrics */}
            {metricsData?.requests && (
                <RequestStatistics
                    metricsData={metricsData}
                    flushCache={flushCache}
                />
            )}

            {/* Rate Limiting */}
            {metricsData?.rate_limiting && (
                <RateLimitingMetrics metricsData={metricsData} />
            )}

            {/* Cache Stats Details */}
            {cacheStats?.cache_stats && (
                <CacheDetails cacheStats={cacheStats} />
            )}
        </Container>
    )
}

export default SystemInfo
