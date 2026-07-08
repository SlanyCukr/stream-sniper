'use client'
import { Card } from 'react-bootstrap'

/**
 * Processing Jobs Statistics Component
 */
const ProcessingJobsStatistics = ({ stats }) => (
    <Card>
        <Card.Body>
            <h3 className="section-label mb-3">Processing jobs</h3>
            <div className="stat-grid">
                <div className="stat-tile">
                    <div className="stat-label">Total</div>
                    <div className="stat-value text-phosphor">{stats.processing_jobs.total}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">Pending</div>
                    <div className="stat-value">{stats.processing_jobs.pending || 0}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">In progress</div>
                    <div className="stat-value">{stats.processing_jobs.in_progress || 0}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">Completed</div>
                    <div className="stat-value">{stats.processing_jobs.completed || 0}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">Failed</div>
                    <div className="stat-value">{stats.processing_jobs.failed || 0}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">Recent 24h</div>
                    <div className="stat-value">{stats.processing_jobs.recent_24h || 0}</div>
                </div>
            </div>
        </Card.Body>
    </Card>
)

export default ProcessingJobsStatistics
