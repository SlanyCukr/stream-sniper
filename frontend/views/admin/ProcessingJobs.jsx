'use client'
import { Form } from 'react-bootstrap'
import Select from 'react-select'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ProcessingJobsStatistics from '@/components/admin/tracking/jobs/ProcessingJobsStatistics'
import ProcessingJobsTable from '@/components/admin/tracking/jobs/ProcessingJobsTable'
import { useProcessingJobsController } from '@/hooks/admin/tracking/useProcessingJobsController'

/** @typedef {{status:string, trackedStreamerId:number|string}} JobFilterState */
/** @typedef {{value:number, label:string}} StreamerOption */

/**
 * @param {{filters:JobFilterState, onFilterChange:(key:keyof JobFilterState, value:string|number)=>void, total:number, streamerOptions:StreamerOption[], streamerOptionsDisabled:boolean}} props
 */
const JobFilters = ({
    filters, onFilterChange, total, streamerOptions, streamerOptionsDisabled,
}) => {
    const selectedStreamer = streamerOptions.find(
        option => String(option.value) === String(filters.trackedStreamerId)
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
                    onChange={e => onFilterChange('status', e.target.value)}
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
                    classNamePrefix="rs"
                    instanceId="jobs-streamer-filter-select"
                    inputId="jobs-streamer-filter"
                    options={streamerOptions}
                    value={selectedStreamer}
                    onChange={option => onFilterChange('trackedStreamerId', option?.value ?? '')}
                    placeholder="Filter by streamer"
                    isClearable
                    isDisabled={streamerOptionsDisabled}
                />
            </div>
            <span className="toolbar-readout">
                {total} jobs
            </span>
        </div>
    )
}

const ProcessingJobs = () => {
    const {
        jobsQueryState,
        statisticsState,
        streamerOptionsState,
        filterProps,
        tableProps,
    } = useProcessingJobsController()

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Processing jobs</h1>
                    <p className="page-sub">Stream processing queue and outcomes</p>
                </div>
            </div>

            <ErrorAlert
                error={jobsQueryState.error}
                title="Processing jobs unavailable"
                onRetry={jobsQueryState.refetch}
                className="mb-4" />

            {statisticsState.error ? (
                <ErrorAlert
                    error={statisticsState.error}
                    title="Processing statistics unavailable"
                    onRetry={statisticsState.refetch}
                    className="mb-4" />
            ) : statisticsState.isLoading ? (
                <LoadingSpinner text="Loading processing statistics..." />
            ) : statisticsState.data ? (
                <ProcessingJobsStatistics
                    processingStats={statisticsState.data}
                    card={false}
                    heading="" />
            ) : null}

            <ErrorAlert
                error={streamerOptionsState.error}
                title="Streamer filters unavailable"
                onRetry={streamerOptionsState.refetch}
                className="mb-3" />

            <JobFilters {...filterProps} />

            <ProcessingJobsTable {...tableProps} />
        </>
    )
}

export default ProcessingJobs
