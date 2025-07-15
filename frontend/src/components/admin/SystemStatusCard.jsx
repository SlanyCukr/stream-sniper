import {
    Card, Badge,
} from 'react-bootstrap'

/**
 * System Status Card Component
 */
const SystemStatusCard = ({
    stats, getStatusBadge,
}) => (
    <Card>
        <Card.Body>
            <h5>System Status</h5>
            <div className="mb-3">
                <div className="d-flex justify-content-between">
                    <span>Stream Monitoring</span>
                    {getStatusBadge(stats.system_status.monitoring_active)}
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between">
                    <span>Processing Queue</span>
                    <Badge bg={stats.system_status.processing_queue_size > 0 ? 'warning' : 'success'}>
                        {stats.system_status.processing_queue_size} pending
                    </Badge>
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between">
                    <span>Failed Jobs</span>
                    <Badge bg={stats.system_status.failed_jobs > 0 ? 'danger' : 'success'}>
                        {stats.system_status.failed_jobs}
                    </Badge>
                </div>
            </div>
        </Card.Body>
    </Card>
)

export default SystemStatusCard
