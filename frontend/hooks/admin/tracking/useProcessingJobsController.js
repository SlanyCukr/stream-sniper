import { useCallback, useState } from 'react'
import {
    useProcessingJobs,
    useTrackedStreamerOptions,
    useTrackingStats,
} from './useTrackingQueries'

const PAGE_SIZE = 50

/** @typedef {{status:string, trackedStreamerId:number|string}} JobFilterState */

export const useProcessingJobsController = () => {
    const [pageIndex, setPageIndex] = useState(0)
    const [filters, setFilters] = useState({
        status: '',
        trackedStreamerId: '',
    })
    const jobsQuery = useProcessingJobs({
        pageIndex,
        pageSize: PAGE_SIZE,
        ...filters,
    })
    const statsQuery = useTrackingStats()
    const streamerOptionsQuery = useTrackedStreamerOptions()
    const jobs = jobsQuery.data?.items || []
    const total = jobsQuery.data?.total || 0
    const pageCount = jobsQuery.data?.pageCount || 0
    const streamerOptions = streamerOptionsQuery.data || []

    const handleFilterChange = useCallback((/** @type {keyof JobFilterState} */ key, /** @type {string|number} */ value) => {
        setFilters(current => ({
            ...current,
            [key]: value,
        }))
        setPageIndex(0)
    }, [])

    return {
        jobsQueryState: {
            error: jobsQuery.error,
            refetch: jobsQuery.refetch,
        },
        statisticsState: {
            data: statsQuery.data?.processingJobs,
            error: statsQuery.error,
            isLoading: statsQuery.isPending,
            refetch: statsQuery.refetch,
        },
        streamerOptionsState: {
            error: streamerOptionsQuery.error,
            refetch: streamerOptionsQuery.refetch,
        },
        filterProps: {
            filters,
            onFilterChange: handleFilterChange,
            total,
            streamerOptions,
            streamerOptionsDisabled: streamerOptionsQuery.isPending || Boolean(streamerOptionsQuery.error),
        },
        tableProps: {
            jobs,
            total,
            loading: jobsQuery.isPending,
            pageIndex,
            pageCount,
            onPageChange: setPageIndex,
        },
    }
}
