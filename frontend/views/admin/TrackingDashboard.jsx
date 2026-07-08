'use client'
import {
    useState, useEffect, useCallback,
} from 'react'
import {
    Container, Row, Col, Alert, Spinner,
} from 'react-bootstrap'
import SystemStatusCard from '@/components/admin/SystemStatusCard'
import TrackedStreamersCard from '@/components/admin/TrackedStreamersCard'
import ProcessingOverviewCard from '@/components/admin/ProcessingOverviewCard'
import ProcessingJobsStatistics from '@/components/admin/ProcessingJobsStatistics'
import TrackingDashboardActions from '@/components/admin/TrackingDashboardActions'
import { api } from '@/lib/api'

const TrackingDashboard = () => {
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

            const { data } = await api.get('/admin/tracking/stats')
            setStats(data)
        } catch (fetchError) {
            console.error('Error fetching stats:', fetchError)
            setError(fetchError.response?.data?.detail || fetchError.message || 'Failed to fetch stats')
        } finally {
            setLoading(false)
        }
    }, [
    ])

    useEffect(() => {
        fetchStats()
        const interval = setInterval(fetchStats, 30000) // Update every 30 seconds
        return () => clearInterval(interval)
    }, [
        fetchStats,
    ])

    const getHealthBadge = isHealthy => isHealthy ?
        <span className="status-chip is-ok">Healthy</span> :
        <span className="status-chip is-err">Unhealthy</span>

    const getStatusBadge = isActive => isActive ?
        <span className="status-chip is-ok">Active</span> :
        <span className="status-chip">Inactive</span>

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
            <div className="page-head">
                <div>
                    <h1 className="page-title">Tracking dashboard</h1>
                    <p className="page-sub">Automated stream tracking · processing system</p>
                </div>
                {stats && (
                    <div className="page-actions">
                        <span className="mono small text-muted">Last updated: {new Date().toLocaleTimeString()}</span>
                    </div>
                )}
            </div>

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
