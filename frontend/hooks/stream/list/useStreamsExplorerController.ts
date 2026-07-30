import {
    mapCreatorOption, useCreators, type CreatorOption,
} from '@/hooks/creator/useCreatorsQuery'
import { usePagedFilters } from '@/hooks/usePagedFilters'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { AVAILABLE_ORDERING, DEFAULT_ORDERING } from '@/lib/stream/config'
import { useStreams } from './useStreamsQuery'

export interface OrderingOption {
    label: string
    value: string
}

export interface StreamFilters {
    creator: CreatorOption | null
    order: OrderingOption | null
    dir: 'asc' | 'desc'
    title: string
    dateFrom: string
    dateTo: string
    minMessages: string
}

export type StreamFilterKey = keyof StreamFilters
export type StreamFilterChange = <K extends StreamFilterKey>(
    key: K,
    value: StreamFilters[K],
) => void

const DEFAULT_FILTERS: StreamFilters = {
    creator: null,
    order: DEFAULT_ORDERING,
    dir: 'desc',
    title: '',
    dateFrom: '',
    dateTo: '',
    minMessages: '',
}

const hasInvalidDateRange = (filters: StreamFilters): boolean => (
    Boolean(filters.dateFrom)
    && Boolean(filters.dateTo)
    && filters.dateFrom > filters.dateTo
)

const hasActiveFilters = (filters: StreamFilters): boolean => (
    Boolean(filters.creator)
    || (filters.order?.value ?? DEFAULT_ORDERING.value) !== DEFAULT_ORDERING.value
    || filters.dir !== 'desc'
    || filters.title !== ''
    || filters.dateFrom !== ''
    || filters.dateTo !== ''
    || filters.minMessages !== ''
)

export const useStreamsExplorerController = () => {
    const {
        pageIndex, setPageIndex, filters, setFilter, resetFilters,
    } = usePagedFilters(DEFAULT_FILTERS)
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

    const handleFilterChange: StreamFilterChange = setFilter
    const handleReset = resetFilters

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
