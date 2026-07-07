'use client'
import {
    Card, Badge, ProgressBar,
} from 'react-bootstrap'

/**
 * Processing Overview Card Component
 */
const ProcessingOverviewCard = ({
    stats, calculateSuccessRate,
}) => {
    const successRate = calculateSuccessRate(stats.processing_jobs.completed, stats.processing_jobs.total)

    return (
        <Card>
            <Card.Body>
                <h5>Processing Overview</h5>
                <div className="mb-3">
                    <div className="d-flex justify-content-between">
                        <span>Success Rate</span>
                        <Badge bg="success">{successRate}%</Badge>
                    </div>
                    <ProgressBar
                        now={successRate}
                        variant="success"
                        className="mt-2"
                    />
                </div>
                <div className="mb-3">
                    <div className="d-flex justify-content-between">
                        <span>Recent Activity</span>
                        <Badge bg="info">{stats.processing_jobs.recent_24h} jobs (24h)</Badge>
                    </div>
                </div>
            </Card.Body>
        </Card>
    )
}

export default ProcessingOverviewCard
