'use client'
import {
    useState, useCallback, useMemo,
} from 'react'
import {
    useStreams, useCreators,
} from '@/hooks/useApiQuery'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { PAGINATION, DEFAULT_ORDERING } from '@/constants'
import StreamThumbnail from '@/components/StreamThumbnail'
import StreamGridSkeleton from '@/components/streams/StreamGridSkeleton'
import ErrorDisplay from '@/components/streams/ErrorDisplay'
import FiltersCard from '@/components/streams/FiltersCard'
import PaginationComponent from '@/components/streams/PaginationComponent'

const DEFAULT_FILTERS = {
    creator: null,
    order: DEFAULT_ORDERING,
    dir: 'desc',
    title: '',
    dateFrom: '',
    dateTo: '',
    minMessages: '',
}

const AllStreams = () => {
    const [
        offset,
        setOffset,
    ] = useState(0)
    const [
        filters,
        setFilters,
    ] = useState(DEFAULT_FILTERS)

    // Debounce free-text title search before it reaches the query; every other
    // filter (creator, sort, direction, dates, min-messages) applies immediately.
    const debouncedTitle = useDebouncedValue(filters.title, 300)

    /**
     * Updates a single filter field and resets pagination to the first page.
     * @param {string} key
     * @param {*} value
     */
    const updateFilter = useCallback((key, value) => {
        setFilters(prev => ({
            ...prev,
            [key]: value,
        }))
        setOffset(0)
    }, [
    ])

    const handleCreatorChange = useCallback(option => updateFilter('creator', option), [
        updateFilter,
    ])

    const handleOrderChange = useCallback(option => updateFilter('order', option), [
        updateFilter,
    ])

    const handleDirToggle = useCallback(() => {
        updateFilter('dir', filters.dir === 'asc' ? 'desc' : 'asc')
    }, [
        updateFilter,
        filters.dir,
    ])

    const handleTitleChange = useCallback(value => updateFilter('title', value), [
        updateFilter,
    ])

    const handleDateFromChange = useCallback(value => updateFilter('dateFrom', value), [
        updateFilter,
    ])

    const handleDateToChange = useCallback(value => updateFilter('dateTo', value), [
        updateFilter,
    ])

    const handleMinMessagesCommit = useCallback(value => updateFilter('minMessages', value), [
        updateFilter,
    ])

    const handleReset = useCallback(() => {
        setFilters(DEFAULT_FILTERS)
        setOffset(0)
    }, [
    ])

    // "From" must not be after "To" — if inverted, warn and drop the date range
    // from the outgoing query instead of sending a range that matches nothing.
    const dateRangeInvalid = useMemo(() => (
        Boolean(filters.dateFrom) && Boolean(filters.dateTo) && filters.dateFrom > filters.dateTo
    ), [
        filters.dateFrom,
        filters.dateTo,
    ])

    const isFiltersDefault = useMemo(() => (
        !filters.creator &&
        (filters.order?.value ?? DEFAULT_ORDERING.value) === DEFAULT_ORDERING.value &&
        filters.dir === 'desc' &&
        filters.title === '' &&
        filters.dateFrom === '' &&
        filters.dateTo === '' &&
        filters.minMessages === ''
    ), [
        filters,
    ])

    // Use TanStack Query hooks for API calls
    const {
        data: streamsData,
        isLoading: streamsLoading,
        error: streamsError,
        refetch: refetchStreams,
    } = useStreams({
        creatorId: filters.creator?.value ?? -1,
        sort: filters.order?.value ?? DEFAULT_ORDERING.value,
        dir: filters.dir,
        title: debouncedTitle || undefined,
        dateFrom: dateRangeInvalid ? undefined : (filters.dateFrom || undefined),
        dateTo: dateRangeInvalid ? undefined : (filters.dateTo || undefined),
        minMessages: filters.minMessages !== '' ? Number(filters.minMessages) : undefined,
        offset,
    })

    const {
        data: creatorsData,
        isLoading: creatorsLoading,
        error: creatorsError,
        refetch: refetchCreators,
    } = useCreators()

    // Transform creators data for react-select with memoization
    const creators = useMemo(() => creatorsData?.map(creator => ({
        label: creator[1],
        value: creator[0],
    })) || [
    ], [
        creatorsData,
    ])

    // Extract streams and pagination data with memoization
    const streams = useMemo(() => streamsData?.streams || [
    ], [
        streamsData?.streams,
    ])

    const maxOffset = useMemo(() => streamsData?.max_offset || 0, [
        streamsData?.max_offset,
    ])

    // Combined loading state with memoization
    const isLoading = useMemo(() => streamsLoading || creatorsLoading, [
        streamsLoading,
        creatorsLoading,
    ])

    /**
     * Updates offset
     * @param {Number} offsetParam
     */
    const updateOffset = useCallback(offsetParam => {
        setOffset(offsetParam)
    }, [
    ])

    // Calculate pages count with memoization
    const pagesCount = useMemo(() => Math.floor(maxOffset / PAGINATION.ITEMS_PER_PAGE), [
        maxOffset,
    ])

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 id="streams-heading" className="page-title">All streams</h1>
                    <p className="page-sub">Captured VODs · chat intelligence</p>
                </div>
            </div>

            <ErrorDisplay
                streamsError={streamsError}
                creatorsError={creatorsError}
                onRetryStreams={refetchStreams}
                onRetryCreators={refetchCreators}
            />

            <FiltersCard
                creators={creators}
                selectedCreator={filters.creator}
                onCreatorChange={handleCreatorChange}
                selectedOrdering={filters.order}
                onOrderChange={handleOrderChange}
                dir={filters.dir}
                onDirToggle={handleDirToggle}
                title={filters.title}
                onTitleChange={handleTitleChange}
                dateFrom={filters.dateFrom}
                dateTo={filters.dateTo}
                onDateFromChange={handleDateFromChange}
                onDateToChange={handleDateToChange}
                dateRangeInvalid={dateRangeInvalid}
                minMessages={filters.minMessages}
                onMinMessagesCommit={handleMinMessagesCommit}
                onReset={handleReset}
                showReset={!isFiltersDefault}
                page={offset + 1}
                pagesCount={pagesCount}
            />

            {isLoading && <StreamGridSkeleton />}

            {!isLoading && (
                <div
                    role="region"
                    aria-labelledby="streams-heading"
                    aria-live="polite"
                    aria-describedby="streams-description"
                >
                    <div
                        id="streams-description"
                        className="visually-hidden">
                        {streams.length > 0
                            ? `Showing ${streams.length} streams on page ${offset + 1} of ${pagesCount}`
                            : 'No streams found'
                        }
                    </div>

                    {streams.length === 0 ? (
                        <div className="card">
                            <div className="empty-state">
                                <div
                                    className="empty-scope"
                                    aria-hidden="true" />
                                <p className="empty-title">No streams in scope</p>
                                <p className="empty-hint">
                                    No captured streams match this filter yet. Streams appear here once the collector has processed a VOD.
                                </p>
                            </div>
                        </div>
                    ) : (
                        <div className="stream-grid">
                            {streams.map((stream, streamIndex) => (
                                <StreamThumbnail
                                    key={`${stream[0]}-${streamIndex}`}
                                    id={stream[0]}
                                    name={stream[1]}
                                    start={stream[2]}
                                    end={stream[3]}
                                    thumbnailSrc={stream[4]}
                                    messageCount={stream[5]}
                                />
                            ))}
                        </div>
                    )}

                    <PaginationComponent
                        pagesCount={pagesCount}
                        offset={offset}
                        updateOffset={updateOffset}
                    />
                </div>
            )}
        </>
    )
}

export default AllStreams
