'use client'
import { Card } from 'react-bootstrap'
import type { TrackingStats } from '@/hooks/admin/tracking/useTrackingQueries'

type ProcessingStats = TrackingStats['processingJobs']

interface ProcessingJobsStatisticsProps {
    processingStats: Partial<Record<keyof ProcessingStats, number | null>>
    card?: boolean
    heading?: string
}

const ProcessingJobsStatistics = ({
    processingStats,
    card = true,
    heading = 'Processing jobs',
}: ProcessingJobsStatisticsProps) => {
    const content = (
        <>
            {heading && <h3 className="section-label mb-3">{heading}</h3>}
            <div className="stat-grid">
                {([
                    ['Total', 'total'],
                    ['Pending', 'pending'],
                    ['In progress', 'inProgress'],
                    ['Completed', 'completed'],
                    ['Failed', 'failed'],
                    ['Recent 24h', 'recent24h'],
                ] as [string, keyof ProcessingStats][]).map(([label, key]) => (
                    <div className="stat-tile" key={key}>
                        <div className="stat-label">{label}</div>
                        <div className="stat-value">{processingStats?.[key] ?? 0}</div>
                    </div>
                ))}
            </div>
        </>
    )
    return card ? <Card><Card.Body>{content}</Card.Body></Card> : content
}

export default ProcessingJobsStatistics
