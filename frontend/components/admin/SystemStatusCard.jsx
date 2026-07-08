'use client'
import { Card } from 'react-bootstrap'

/**
 * System Status Card Component
 */
const SystemStatusCard = ({
    stats, getStatusBadge,
}) => (
    <Card className="h-100">
        <Card.Body>
            <h3 className="section-label mb-3">System status</h3>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Stream Monitoring</span>
                    {getStatusBadge(stats.system_status.monitoring_active)}
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Processing Queue</span>
                    <span className={`status-chip ${stats.system_status.processing_queue_size > 0 ? 'is-warn' : 'is-ok'}`}>
                        {stats.system_status.processing_queue_size} pending
                    </span>
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Failed Jobs</span>
                    <span className={`status-chip ${stats.system_status.failed_jobs > 0 ? 'is-err' : 'is-ok'}`}>
                        {stats.system_status.failed_jobs}
                    </span>
                </div>
            </div>
        </Card.Body>
    </Card>
)

export default SystemStatusCard
