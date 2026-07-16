'use client'
import { Card } from 'react-bootstrap'

/** @typedef {ReturnType<typeof import('@/hooks/admin/tracking/useTrackingQueries').mapTrackingStats>['processingJobs']} ProcessingStats */

/** @param {{processingStats:Partial<Record<keyof ProcessingStats, number|null>>, card?:boolean, heading?:string}} props */
const ProcessingJobsStatistics = ({
    processingStats,
    card = true,
    heading = 'Processing jobs',
}) => {
    const content = (
        <>
            {heading && <h3 className="section-label mb-3">{heading}</h3>}
            <div className="stat-grid">
                {(/** @type {[string, keyof ProcessingStats][]} */ ([
                    ['Total', 'total'],
                    ['Pending', 'pending'],
                    ['In progress', 'inProgress'],
                    ['Completed', 'completed'],
                    ['Failed', 'failed'],
                    ['Recent 24h', 'recent24h'],
                ])).map(([label, key]) => (
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
