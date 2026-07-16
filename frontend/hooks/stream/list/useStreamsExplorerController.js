import { useCallback, useState } from 'react'
import {
    mapCreatorOption, useCreators,
} from '@/hooks/creator/useCreatorsQuery'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { AVAILABLE_ORDERING, DEFAULT_ORDERING } from '@/lib/stream/config'
import { useStreams } from './useStreamsQuery'

/** @typedef {{label:string, value:number}} CreatorOption */
/** @typedef {{label:string, value:string}} OrderingOption */
/** @typedef {{
 * creator: CreatorOption|null,
 * order: OrderingOption|null,
 * dir: 'asc'|'desc',
 * title: string,
 * dateFrom: string,
 * dateTo: string,
 * minMessages: string,
 * }} StreamFilters */
/** @typedef {keyof StreamFilters} StreamFilterKey */

const DEFAULT_FILTERS = /** @type {StreamFilters} */ ({
    creator: null,
    order: DEFAULT_ORDERING,
    dir: 'desc',
    title: '',
    dateFrom: '',
    dateTo: '',
    minMessages: '',
})

/** @param {StreamFilters} filters */
const hasInvalidDateRange = filters => (
    Boolean(filters.dateFrom)
    && Boolean(filters.dateTo)
    && filters.dateFrom > filters.dateTo
)

/** @param {StreamFilters} filters */
const hasActiveFilters = filters => (
    Boolean(filters.creator)
    || (filters.order?.value ?? DEFAULT_ORDERING.value) !== DEFAULT_ORDERING.value
    || filters.dir !== 'desc'
    || filters.title !== ''
    || filters.dateFrom !== ''
    || filters.dateTo !== ''
    || filters.minMessages !== ''
)

export const useStreamsExplorerController = () => {
    const [pageIndex, setPageIndex] = useState(0)
    const [filters, setFilters] = useState(DEFAULT_FILTERS)
    const debouncedTitle = useDebouncedValue(filters.title, 300)
    const dateRangeInvalid = hasInvalidDateRange(filters)

    const streamsQuery = useStreams({
        creatorId: filters.creator?.value ?? -1,
        sort: filters.order?.value ?? DEFAULT_ORDERING.value,
        dir: filters.dir,
        title: debouncedTitle || undefined,
        dateFrom: dateRangeInvalid ? undefined : (filters.dateFrom || undefined),
        dateTo: dateRangeInvalid ? undefined : (filters.dateTo || undefined),
        minMessages: filters.minMessages !== '' ? Number(filters.minMessages) : undefined,
        pageIndex,
    })
    const creatorsQuery = useCreators()
    const streams = streamsQuery.data?.items || []
    const pageCount = streamsQuery.data?.pageCount || 0

    const handleFilterChange = useCallback((
        /** @type {StreamFilterKey} */ key,
        /** @type {StreamFilters[StreamFilterKey]} */ value,
    ) => {
        setFilters(current => ({
            ...current,
            [key]: value,
        }))
        setPageIndex(0)
    }, [])

    const handleReset = useCallback(() => {
        setFilters(DEFAULT_FILTERS)
        setPageIndex(0)
    }, [])

    return {
        errorDisplayProps: {
            streamsError: streamsQuery.error,
            creatorsError: creatorsQuery.error,
            onRetryStreams: streamsQuery.refetch,
            onRetryCreators: creatorsQuery.refetch,
        },
        filtersCardProps: {
            filters,
            options: {
                creators: creatorsQuery.data?.map(mapCreatorOption) || [],
                ordering: AVAILABLE_ORDERING,
            },
            validation: {
                dateRangeInvalid,
                showReset: hasActiveFilters(filters),
            },
            pagination: {
                pageIndex,
                pageCount,
            },
            onFilterChange: handleFilterChange,
            onReset: handleReset,
        },
        results: {
            streams,
            isLoading: streamsQuery.isLoading || creatorsQuery.isLoading,
            pageIndex,
            pageCount,
            onPageChange: setPageIndex,
        },
    }
}
