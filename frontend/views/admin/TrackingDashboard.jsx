'use client'
import {
    Container, Row, Col, Alert, Spinner,
} from 'react-bootstrap'
import SystemStatusCard from '@/components/admin/SystemStatusCard'
import TrackedStreamersCard from '@/components/admin/TrackedStreamersCard'
import ProcessingOverviewCard from '@/components/admin/ProcessingOverviewCard'
import ProcessingJobsStatistics from '@/components/admin/ProcessingJobsStatistics'
import TrackingDashboardActions from '@/components/admin/TrackingDashboardActions'
import { getApiErrorMessage } from '@/lib/api'
import {
    useTrackingStats,
} from '@/hooks/useTrackingQueries'

const TrackingDashboard = () => {
    const {
        data: stats,
        error,
        isPending: loading,
        refetch: fetchStats,
    } = useTrackingStats({
        refetchInterval: 30000,
    })

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
                    className="mb-4">
                    {getApiErrorMessage(error, 'Failed to fetch tracking statistics')}
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
