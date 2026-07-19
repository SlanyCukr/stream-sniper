'use client'
import type { ReactNode } from 'react'
import { Card } from 'react-bootstrap'
import StatusChip from '@/components/common/StatusChip'
import type { TrackingStats } from '@/hooks/admin/tracking/useTrackingQueries'

const statusBadge = (isActive: boolean): ReactNode => (
    isActive
        ? <StatusChip variant="ok">Active</StatusChip>
        : <StatusChip>Inactive</StatusChip>
)

interface SystemStatusCardProps {
    stats: TrackingStats
}

const SystemStatusCard = ({ stats }: SystemStatusCardProps) => (
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
                    <StatusChip variant={stats.systemStatus.processingQueueSize > 0 ? 'warn' : 'ok'}>
                        {stats.systemStatus.processingQueueSize} pending
                    </StatusChip>
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Failed Jobs</span>
                    <StatusChip variant={stats.systemStatus.failedJobs > 0 ? 'err' : 'ok'}>
                        {stats.systemStatus.failedJobs}
                    </StatusChip>
                </div>
            </div>
        </Card.Body>
    </Card>
)

export default SystemStatusCard
