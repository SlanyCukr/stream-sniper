'use client'
import { useState } from 'react'
import {
    Card, Table, Alert, Spinner, Form, Pagination,
} from 'react-bootstrap'
import Select from 'react-select'
import {
    getApiErrorMessage,
    useProcessingJobs,
    useTrackedStreamerOptions,
    useTrackingStats,
} from '@/hooks/useTrackingQueries'

/**
 * Statistics Tiles Component
 */
const StatisticsCards = ({ stats }) => (
    <div className="stat-grid">
        <div className="stat-tile">
            <div className="stat-label">Total</div>
            <div className="stat-value">{stats.total || 0}</div>
        </div>
        <div className="stat-tile">
            <div className="stat-label">Pending</div>
            <div className="stat-value">{stats.pending || 0}</div>
        </div>
        <div className="stat-tile">
            <div className="stat-label">In Progress</div>
            <div className="stat-value">{stats.in_progress || 0}</div>
        </div>
        <div className="stat-tile">
            <div className="stat-label">Completed</div>
            <div className="stat-value">{stats.completed || 0}</div>
        </div>
        <div className="stat-tile">
            <div className="stat-label">Failed</div>
            <div className="stat-value">{stats.failed || 0}</div>
        </div>
        <div className="stat-tile">
            <div className="stat-label">Recent 24h</div>
            <div className="stat-value">{stats.recent_24h || 0}</div>
        </div>
    </div>
)

/**
 * Filters Toolbar Component
 */
const JobFilters = ({
    filters, setFilters, total, streamerOptions,
}) => {
    const selectedStreamer = streamerOptions.find(
        option => String(option.value) === String(filters.tracked_streamer_id)
    ) || null

    return (
        <div className="toolbar">
            <span
                className="toolbar-label"
                aria-hidden="true">
                Filter
            </span>
            <div className="toolbar-field">
                <label
                    htmlFor="jobs-status-filter"
                    className="visually-hidden"
                >
                    Filter by status
                </label>
                <Form.Select
                    id="jobs-status-filter"
                    value={filters.status}
                    onChange={e => setFilters(prev => ({
                        ...prev,
                        status: e.target.value,
                    }))}
                >
                    <option value="">All statuses</option>
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                    <option value="failed">Failed</option>
                </Form.Select>
            </div>
            <div className="toolbar-field">
                <label
                    htmlFor="jobs-streamer-filter"
                    className="visually-hidden"
                >
                    Filter by streamer
                </label>
                <Select
                    instanceId="jobs-streamer-filter-select"
                    inputId="jobs-streamer-filter"
                    options={streamerOptions}
                    value={selectedStreamer}
                    onChange={option => setFilters(prev => ({
                        ...prev,
                        tracked_streamer_id: option?.value ?? '',
                    }))}
                    placeholder="Filter by streamer"
                    isClearable
                />
            </div>
            <span className="toolbar-readout">
                {total} jobs
            </span>
        </div>
    )
}

const ProcessingJobs = () => {
    const [
        pagination,
        setPagination,
    ] = useState({
        offset: 0,
        limit: 50,
    })
    const [
        filters,
        setFilters,
    ] = useState({
        status: '',
        tracked_streamer_id: '',
    })
    const {
        data: jobsData,
        error: jobsError,
        isPending: loading,
    } = useProcessingJobs({
        ...pagination,
        ...filters,
    })
    const { data: trackingStats } = useTrackingStats()
    const { data: streamerOptions = [] } = useTrackedStreamerOptions()
    const jobs = jobsData?.jobs || []
    const total = jobsData?.total || 0
    const currentPage = Math.floor(pagination.offset / pagination.limit) + 1
    const error = jobsError && getApiErrorMessage(jobsError, 'Failed to fetch processing jobs')
    const stats = trackingStats?.processing_jobs || {}

    const handlePageChange = page => {
        setPagination(prev => ({
            ...prev,
            offset: (page - 1) * prev.limit,
        }))
    }

    const formatDateTime = dateString => {
        if (!dateString) {
            return 'N/A'
        }
        return new Date(dateString).toLocaleString()
    }

    const getDuration = (startTime, endTime) => {
        if (!startTime || !endTime) {
            return 'N/A'
        }
        const start = new Date(startTime)
        const end = new Date(endTime)
        const duration = Math.floor((end - start) / 1000)
        return `${duration}s`
    }

    const getStatusChip = status => {
        const modifiers = {
            'pending': ' is-warn',
            'in_progress': ' is-warn',
            'completed': ' is-ok',
            'failed': ' is-err',
        }
        return (
            <span className={`status-chip${modifiers[status] || ''}`}>
                {status === 'in_progress' ? 'in progress' : status}
            </span>
        )
    }

    const totalPages = Math.ceil(total / pagination.limit)

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Processing jobs</h1>
                    <p className="page-sub">Stream processing queue and outcomes</p>
                </div>
            </div>

            {error && (
                <Alert
                    variant="danger"
                    className="mb-4">
                    {error}
                </Alert>
            )}

            <StatisticsCards stats={stats} />

            <JobFilters
                filters={filters}
                setFilters={setFilters}
                total={total}
                streamerOptions={streamerOptions} />

            <Card>
                <Card.Body className={!loading && jobs.length === 0 ? 'p-0' : ''}>
                    {loading ? (
                        <div className="text-center py-5">
                            <Spinner
                                animation="border"
                                variant="primary" />
                        </div>
                    ) : jobs.length === 0 ? (
                        <div className="empty-state">
                            <div
                                className="empty-scope"
                                aria-hidden="true" />
                            <p className="empty-title">No processing jobs</p>
                            <p className="empty-hint">
                                No jobs match this filter. Jobs appear here once tracked streamers have streams queued for processing.
                            </p>
                        </div>
                    ) : (
                        <>
                            <Table
                                hover
                                responsive>
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Streamer</th>
                                        <th>Stream ID</th>
                                        <th>Status</th>
                                        <th>Created</th>
                                        <th>Started</th>
                                        <th>Completed</th>
                                        <th>Duration</th>
                                        <th>Retries</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {jobs.map(job => (
                                        <tr key={job.id}>
                                            <td className="mono">{job.id}</td>
                                            <td>
                                                <strong>{job.twitch_username}</strong>
                                                {job.streamer_display_name && (
                                                    <small className="text-muted d-block">
                                                        {job.streamer_display_name}
                                                    </small>
                                                )}
                                            </td>
                                            <td className="mono">{job.twitch_stream_id}</td>
                                            <td>{getStatusChip(job.status)}</td>
                                            <td className="mono">{formatDateTime(job.created_at)}</td>
                                            <td className="mono">{formatDateTime(job.started_at)}</td>
                                            <td className="mono">{formatDateTime(job.completed_at)}</td>
                                            <td className="mono">{getDuration(job.started_at, job.completed_at)}</td>
                                            <td className="mono">
                                                {job.retry_count > 0 && (
                                                    <span className="status-chip is-warn">{job.retry_count}</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </Table>

                            <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mt-3">
                                <span className="mono small text-muted">
                                    Showing {jobs.length} of {total}
                                </span>
                                {totalPages > 1 && (
                                    <Pagination className="mb-0">
                                        <Pagination.First
                                            onClick={() => handlePageChange(1)}
                                            disabled={currentPage === 1}
                                        />
                                        <Pagination.Prev
                                            onClick={() => handlePageChange(currentPage - 1)}
                                            disabled={currentPage === 1}
                                        />
                                        {[
                                            ...Array(Math.min(5, totalPages)),
                                        ].map((_, i) => {
                                            const page = Math.max(1, currentPage - 2) + i
                                            if (page <= totalPages) {
                                                return (
                                                    <Pagination.Item
                                                        key={page}
                                                        active={page === currentPage}
                                                        onClick={() => handlePageChange(page)}
                                                    >
                                                        {page}
                                                    </Pagination.Item>
                                                )
                                            }
                                            return null
                                        })}
                                        <Pagination.Next
                                            onClick={() => handlePageChange(currentPage + 1)}
                                            disabled={currentPage === totalPages}
                                        />
                                        <Pagination.Last
                                            onClick={() => handlePageChange(totalPages)}
                                            disabled={currentPage === totalPages}
                                        />
                                    </Pagination>
                                )}
                            </div>
                        </>
                    )}
                </Card.Body>
            </Card>
        </>
    )
}

export default ProcessingJobs
