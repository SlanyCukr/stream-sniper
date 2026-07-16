import { Card, Table } from 'react-bootstrap'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import PaginatedResultsFooter from '@/components/common/pagination/PaginatedResultsFooter'

/** @typedef {ReturnType<typeof import('@/hooks/admin/tracking/useTrackingQueries').mapProcessingJob>} ProcessingJob */

/** @param {string|null} dateString */
const formatDateTime = dateString => dateString
    ? new Date(dateString).toLocaleString()
    : 'N/A'

/** @param {string|null} startTime @param {string|null} endTime */
const formatDuration = (startTime, endTime) => {
    if (!startTime || !endTime) return 'N/A'
    const durationSeconds = Math.floor(
        (new Date(endTime).getTime() - new Date(startTime).getTime()) / 1000,
    )
    return `${durationSeconds}s`
}

const STATUS_MODIFIERS = {
    pending: ' is-warn',
    in_progress: ' is-warn',
    completed: ' is-ok',
    failed: ' is-err',
}

/** @param {{status:string}} props */
const StatusChip = ({ status }) => (
    <span className={`status-chip${STATUS_MODIFIERS[/** @type {keyof typeof STATUS_MODIFIERS} */ (status)] || ''}`}>
        {status === 'in_progress' ? 'in progress' : status}
    </span>
)

/**
 * @param {{jobs:ProcessingJob[], total:number, loading:boolean, pageIndex:number, pageCount:number, onPageChange:(pageIndex:number)=>void}} props
 */
const ProcessingJobsTable = ({
    jobs,
    total,
    loading,
    pageIndex,
    pageCount,
    onPageChange,
}) => (
    <Card>
        <Card.Body className={!loading && jobs.length === 0 ? 'p-0' : ''}>
            {loading ? (
                <LoadingSpinner text="Loading processing jobs..." />
            ) : jobs.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-scope" aria-hidden="true" />
                    <p className="empty-title">No processing jobs</p>
                    <p className="empty-hint">
                        No jobs match this filter. Jobs appear here once tracked streamers have streams queued for processing.
                    </p>
                </div>
            ) : (
                <>
                    <Table hover responsive>
                        <thead>
                            <tr>
                                <th scope="col">ID</th>
                                <th scope="col">Streamer</th>
                                <th scope="col">Stream ID</th>
                                <th scope="col">Status</th>
                                <th scope="col">Created</th>
                                <th scope="col">Started</th>
                                <th scope="col">Completed</th>
                                <th scope="col">Duration</th>
                                <th scope="col">Retries</th>
                            </tr>
                        </thead>
                        <tbody>
                            {jobs.map(job => (
                                <tr key={job.id}>
                                    <td className="mono">{job.id}</td>
                                    <td>
                                        <strong>{job.twitchUsername}</strong>
                                        {job.streamerDisplayName && (
                                            <small className="text-muted d-block">
                                                {job.streamerDisplayName}
                                            </small>
                                        )}
                                    </td>
                                    <td className="mono">{job.twitchVodId}</td>
                                    <td><StatusChip status={job.status} /></td>
                                    <td className="mono">{formatDateTime(job.createdAt)}</td>
                                    <td className="mono">{formatDateTime(job.startedAt)}</td>
                                    <td className="mono">{formatDateTime(job.completedAt)}</td>
                                    <td className="mono">{formatDuration(job.startedAt, job.completedAt)}</td>
                                    <td className="mono">
                                        {job.retryCount > 0 && (
                                            <span className="status-chip is-warn">{job.retryCount}</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </Table>

                    <PaginatedResultsFooter
                        shown={jobs.length}
                        total={total}
                        pageIndex={pageIndex}
                        pageCount={pageCount}
                        onPageChange={onPageChange}
                        ariaLabel="Processing jobs pagination"
                    />
                </>
            )}
        </Card.Body>
    </Card>
)

export default ProcessingJobsTable
