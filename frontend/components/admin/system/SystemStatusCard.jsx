'use client'
import { Card } from 'react-bootstrap'

/** @typedef {ReturnType<typeof import('@/hooks/admin/tracking/useTrackingQueries').mapTrackingStats>} TrackingStats */

/** @param {boolean} isActive */
const statusBadge = isActive => (
    isActive
        ? <span className="status-chip is-ok">Active</span>
        : <span className="status-chip">Inactive</span>
)

/** @param {{stats:TrackingStats}} props */
const SystemStatusCard = ({ stats }) => (
    <Card className="h-100">
        <Card.Body>
            <h3 className="section-label mb-3">System status</h3>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Stream Monitoring</span>
                    {statusBadge(
                        stats.systemStatus.monitoringActive &&
                        !stats.systemStatus.monitoringDegraded,
                    )}
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Processing Queue</span>
                    <span className={`status-chip ${stats.systemStatus.processingQueueSize > 0 ? 'is-warn' : 'is-ok'}`}>
                        {stats.systemStatus.processingQueueSize} pending
                    </span>
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Failed Jobs</span>
                    <span className={`status-chip ${stats.systemStatus.failedJobs > 0 ? 'is-err' : 'is-ok'}`}>
                        {stats.systemStatus.failedJobs}
                    </span>
                </div>
            </div>
        </Card.Body>
    </Card>
)

export default SystemStatusCard
