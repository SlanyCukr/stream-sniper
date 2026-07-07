'use client'
import {
    useState, useEffect, useCallback,
} from 'react'
import {
    Container,
    Row,
    Col,
    Alert,
    Spinner,
    Badge,
    Button,
} from 'react-bootstrap'
import SystemHealthOverview from '@/components/admin/SystemHealthOverview'
import ComponentsHealth from '@/components/admin/ComponentsHealth'
import RequestStatistics from '@/components/admin/RequestStatistics'
import RateLimitingMetrics from '@/components/admin/RateLimitingMetrics'
import RedisCacheDetails from '@/components/admin/RedisCacheDetails'
import { api } from '@/lib/api'


const SystemInfo = () => {
    const [
        healthData,
        setHealthData,
    ] = useState(null)
    const [
        metricsData,
        setMetricsData,
    ] = useState(null)
    const [
        cacheStats,
        setCacheStats,
    ] = useState(null)
    const [
        loading,
        setLoading,
    ] = useState(true)
    const [
        error,
        setError,
    ] = useState(null)

    const fetchSystemInfo = useCallback(async () => {
        setLoading(true)
        setError(null)

        // Fetch each endpoint independently so one failure does not blank the others
        try {
            const { data } = await api.get('/health/detailed')
            setHealthData(data)
        } catch (healthError) {
            console.error('Error fetching health data:', healthError)
        }

        try {
            const { data } = await api.get('/metrics')
            setMetricsData(data)
        } catch (metricsError) {
            console.error('Error fetching metrics:', metricsError)
        }

        try {
            const { data } = await api.get('/cache/stats')
            setCacheStats(data)
        } catch (cacheError) {
            console.error('Error fetching cache stats:', cacheError)
        }

        setLoading(false)
    }, [
    ])

    useEffect(() => {
        fetchSystemInfo()
    }, [
        fetchSystemInfo,
    ])

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
            'healthy': 'success',
            'degraded': 'warning',
            'unhealthy': 'danger',
            'critical': 'danger',
        }
        return <Badge bg={statusMap[status] || 'secondary'}>{status}</Badge>
    }

    const flushCache = async () => {
        try {
            await api.post('/cache/flush')
            alert('Cache flushed successfully')
            fetchSystemInfo()
        } catch (flushError) {
            console.error('Error flushing cache:', flushError)
            setError(flushError.response?.data?.detail || flushError.message || 'Error flushing cache')
            alert('Error flushing cache: ' + (flushError.response?.data?.detail || flushError.message))
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
            <Row className="mb-4">
                <Col>
                    <h2>System Information</h2>
                    <p className="text-muted">System health, performance metrics, and monitoring data</p>
                </Col>
                <Col xs="auto">
                    <Button
                        variant="outline-primary"
                        onClick={fetchSystemInfo}>
                        <i className="bi bi-arrow-clockwise me-2"></i>
                        Refresh
                    </Button>
                </Col>
            </Row>

            {error && (
                <Alert
                    variant="danger"
                    className="mb-4">
                    {error}
                </Alert>
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
            {cacheStats?.redis_stats && (
                <RedisCacheDetails
                    cacheStats={cacheStats}
                    formatUptime={formatUptime}
                />
            )}
        </Container>
    )
}

export default SystemInfo
