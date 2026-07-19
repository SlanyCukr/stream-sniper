'use client'
import {
    Card, ProgressBar,
} from 'react-bootstrap'
import type { TrackingStats } from '@/hooks/admin/tracking/useTrackingQueries'

interface ProcessingOverviewCardProps {
    stats: TrackingStats
}

const ProcessingOverviewCard = ({
    stats,
}: ProcessingOverviewCardProps) => {
    const { completed, total } = stats.processingJobs
    const successRate = total === 0 ? 0 : Math.round((completed / total) * 100)

    return (
        <Card className="h-100">
            <Card.Body>
                <h3 className="section-label mb-3">Processing overview</h3>
                <div className="mb-3">
                    <div className="d-flex justify-content-between align-items-center">
                        <span>Success Rate</span>
                        <span className="mono">{successRate}%</span>
                    </div>
                    <ProgressBar
                        now={successRate}
                        variant="success"
                        className="mt-2"
                    />
                </div>
                <div className="mb-3">
                    <div className="d-flex justify-content-between align-items-center">
                        <span>Recent Activity</span>
                        <span className="mono">{stats.processingJobs.recent24h} jobs (24h)</span>
                    </div>
                </div>
            </Card.Body>
        </Card>
    )
}

export default ProcessingOverviewCard
