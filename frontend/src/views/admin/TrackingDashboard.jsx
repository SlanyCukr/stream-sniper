import {
    useState, useEffect, useCallback,
} from 'react'
import {
    Container, Row, Col, Alert, Spinner, Badge,
} from 'react-bootstrap'
import { useAuth } from '../../contexts/AuthContext'
import SystemStatusCard from '../../components/admin/SystemStatusCard'
import TrackedStreamersCard from '../../components/admin/TrackedStreamersCard'
import ProcessingOverviewCard from '../../components/admin/ProcessingOverviewCard'
import ProcessingJobsStatistics from '../../components/admin/ProcessingJobsStatistics'
import TrackingDashboardActions from '../../components/admin/TrackingDashboardActions'

// Use environment variable from build time, fallback to /api for production
const API_URL = process.env.REACT_APP_API_URL || '/api'

const TrackingDashboard = () => {
    const {
        token,
    } = useAuth()
    const [
        stats,
        setStats,
    ] = useState(null)
    const [
        loading,
        setLoading,
    ] = useState(true)
    const [
        error,
        setError,
    ] = useState(null)

    const fetchStats = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            const response = await fetch(`${API_URL}/admin/tracking/stats`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            })

            if (response.ok) {
                const data = await response.json()
                setStats(data)
            } else {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Failed to fetch stats')
            }
        } catch (fetchError) {
            console.error('Error fetching stats:', fetchError)
            setError(fetchError.message)
        } finally {
            setLoading(false)
        }
    }, [
        token,
    ])

    useEffect(() => {
        fetchStats()
        const interval = setInterval(fetchStats, 30000) // Update every 30 seconds
        return () => clearInterval(interval)
    }, [
        fetchStats,
    ])

    const getHealthBadge = isHealthy => isHealthy ?
        <Badge bg="success">Healthy</Badge> :
        <Badge bg="danger">Unhealthy</Badge>

    const getStatusBadge = isActive => isActive ?
        <Badge bg="success">Active</Badge> :
        <Badge bg="secondary">Inactive</Badge>

    const calculateSuccessRate = (completed, total) => {
        if (total === 0) {
            return 0
        }
        return Math.round((completed / total) * 100)
    }

    if (loading && !stats) {
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
        <Container fluid>
            <Row className="mb-4">
                <Col>
                    <h2>Tracking Dashboard</h2>
                    <p className="text-muted">
                        Overview of automated stream tracking and processing system
                        {stats && <small className="ms-2">Last updated: {new Date().toLocaleTimeString()}</small>}
                    </p>
                </Col>
            </Row>

            {error && (
                <Alert
                    variant="danger"
                    className="mb-4"
                    dismissible
                    onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {stats && (
                <>
                    <Row className="mb-4">
                        <Col md={4}>
                            <SystemStatusCard
                                stats={stats}
                                getStatusBadge={getStatusBadge} />
                        </Col>
                        <Col md={4}>
                            <TrackedStreamersCard stats={stats} />
                        </Col>
                        <Col md={4}>
                            <ProcessingOverviewCard
                                stats={stats}
                                calculateSuccessRate={calculateSuccessRate} />
                        </Col>
                    </Row>

                    {/* Processing Jobs Statistics */}
                    <Row className="mb-4">
                        <Col>
                            <ProcessingJobsStatistics stats={stats} />
                        </Col>
                    </Row>

                    {/* Quick Actions and System Health */}
                    <TrackingDashboardActions
                        stats={stats}
                        getHealthBadge={getHealthBadge}
                        fetchStats={fetchStats}
                        loading={loading}
                    />
                </>
            )}
        </Container>
    )
}

export default TrackingDashboard
