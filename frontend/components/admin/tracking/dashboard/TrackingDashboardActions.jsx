'use client'
import {
    Row, Col, Card,
} from 'react-bootstrap'
import Link from 'next/link'

/** @typedef {ReturnType<typeof import('@/hooks/admin/tracking/useTrackingQueries').mapTrackingStats>} TrackingStats */

/** @param {boolean} isHealthy */
const healthBadge = isHealthy => (
    isHealthy
        ? <span className="status-chip is-ok">Healthy</span>
        : <span className="status-chip is-err">Unhealthy</span>
)

/** @param {{stats:TrackingStats, fetchStats:()=>unknown, loading:boolean}} props */
const TrackingDashboardActions = ({
    stats, fetchStats, loading,
}) => (
    <Row>
        <Col md={6}>
            <Card className="mb-4">
                <Card.Body>
                    <h3 className="section-label mb-3">Quick actions</h3>
                    <div className="d-grid gap-2">
                        <Link
                            href="/admin/tracking/streamers"
                            className="btn btn-primary">
                            <i
                                className="bi bi-people me-2"
                                aria-hidden="true" />
                            Manage Tracked Streamers
                        </Link>
                        <Link
                            href="/admin/tracking/jobs"
                            className="btn btn-outline-primary">
                            <i
                                className="bi bi-list-check me-2"
                                aria-hidden="true" />
                            View Processing Jobs
                        </Link>
                        <button
                            className="btn btn-outline-primary"
                            onClick={fetchStats}
                            disabled={loading}
                        >
                            <i
                                className="bi bi-arrow-clockwise me-2"
                                aria-hidden="true" />
                            Refresh Statistics
                        </button>
                    </div>
                </Card.Body>
            </Card>
        </Col>
        <Col md={6}>
            <Card className="mb-4">
                <Card.Body>
                    <h3 className="section-label mb-3">System health</h3>
                    <div className="mb-3">
                        <div className="d-flex justify-content-between align-items-center">
                            <span>Overall System</span>
                            {healthBadge(
                                stats.systemStatus.monitoringActive &&
                                !stats.systemStatus.monitoringDegraded &&
                                stats.systemStatus.failedJobs === 0,
                            )}
                        </div>
                    </div>
                    <div className="mb-3">
                        <div className="d-flex justify-content-between align-items-center">
                            <span>Stream Monitoring</span>
                            {healthBadge(
                                stats.systemStatus.monitoringActive &&
                                !stats.systemStatus.monitoringDegraded,
                            )}
                        </div>
                    </div>
                    <div className="mb-3">
                        <div className="d-flex justify-content-between align-items-center">
                            <span>Processing Queue</span>
                            {healthBadge(stats.systemStatus.processingQueueSize < 100)}
                        </div>
                    </div>
                    <div className="mb-3">
                        <div className="d-flex justify-content-between align-items-center">
                            <span>Error Rate</span>
                            {healthBadge(stats.systemStatus.failedJobs < 10)}
                        </div>
                    </div>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default TrackingDashboardActions
