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
import { useAuth } from '../../contexts/AuthContext'
import SystemHealthOverview from '../../components/admin/SystemHealthOverview'
import ComponentsHealth from '../../components/admin/ComponentsHealth'
import RequestStatistics from '../../components/admin/RequestStatistics'
import RateLimitingMetrics from '../../components/admin/RateLimitingMetrics'
import RedisCacheDetails from '../../components/admin/RedisCacheDetails'

// Use environment variable from build time, fallback to /api for production
const API_URL = process.env.REACT_APP_API_URL || '/api'


const SystemInfo = () => {
    const { token } = useAuth()
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
        try {
            setLoading(true)
            setError(null)

            // Fetch health data
            const healthResponse = await fetch(`${API_URL}/health/detailed`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            })

            if (healthResponse.ok) {
                const health = await healthResponse.json()
                setHealthData(health)
            }

            // Fetch metrics data
            const metricsResponse = await fetch(`${API_URL}/metrics`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            })

            if (metricsResponse.ok) {
                const metrics = await metricsResponse.json()
                setMetricsData(metrics)
            }

            // Fetch cache stats
            const cacheResponse = await fetch(`${API_URL}/cache/stats`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            })

            if (cacheResponse.ok) {
                const cache = await cacheResponse.json()
                setCacheStats(cache)
            }

        } catch (fetchError) {
            console.error('Error fetching system info:', fetchError)
            setError(fetchError.message)
        } finally {
            setLoading(false)
        }
    }, [
        token,
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
            const response = await fetch(`${API_URL}/cache/flush`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            })

            if (response.ok) {
                alert('Cache flushed successfully')
                fetchSystemInfo()
            } else {
                throw new Error('Failed to flush cache')
            }
        } catch (flushError) {
            console.error('Error flushing cache:', flushError)
            alert('Error flushing cache: ' + flushError.message)
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
