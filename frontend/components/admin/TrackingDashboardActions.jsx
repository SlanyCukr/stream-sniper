'use client'
import {
    Row, Col, Card,
} from 'react-bootstrap'

/**
 * Tracking Dashboard Actions and System Health Component
 */
const TrackingDashboardActions = ({
    stats, getHealthBadge, fetchStats, loading,
}) => (
    <Row>
        <Col md={6}>
            <Card>
                <Card.Header>
                    <Card.Title>Quick Actions</Card.Title>
                </Card.Header>
                <Card.Body>
                    <div className="d-grid gap-2">
                        <a
                            href="/admin/tracking/streamers"
                            className="btn btn-primary">
                            <i className="bi bi-people me-2"></i>
                            Manage Tracked Streamers
                        </a>
                        <a
                            href="/admin/tracking/jobs"
                            className="btn btn-info">
                            <i className="bi bi-list-check me-2"></i>
                            View Processing Jobs
                        </a>
                        <button
                            className="btn btn-success"
                            onClick={fetchStats}
                            disabled={loading}
                        >
                            <i className="bi bi-arrow-clockwise me-2"></i>
                            Refresh Statistics
                        </button>
                    </div>
                </Card.Body>
            </Card>
        </Col>
        <Col md={6}>
            <Card>
                <Card.Header>
                    <Card.Title>System Health</Card.Title>
                </Card.Header>
                <Card.Body>
                    <div className="mb-3">
                        <div className="d-flex justify-content-between">
                            <span>Overall System</span>
                            {getHealthBadge(
                                stats.system_status.monitoring_active &&
                                stats.system_status.failed_jobs === 0,
                            )}
                        </div>
                    </div>
                    <div className="mb-3">
                        <div className="d-flex justify-content-between">
                            <span>Stream Monitoring</span>
                            {getHealthBadge(stats.system_status.monitoring_active)}
                        </div>
                    </div>
                    <div className="mb-3">
                        <div className="d-flex justify-content-between">
                            <span>Processing Queue</span>
                            {getHealthBadge(stats.system_status.processing_queue_size < 100)}
                        </div>
                    </div>
                    <div className="mb-3">
                        <div className="d-flex justify-content-between">
                            <span>Error Rate</span>
                            {getHealthBadge(stats.system_status.failed_jobs < 10)}
                        </div>
                    </div>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default TrackingDashboardActions
