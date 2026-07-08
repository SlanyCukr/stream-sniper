'use client'
import {
    useState, useCallback, useMemo,
} from 'react'
import {
    useStreams, useCreators,
} from '@/hooks/useApiQuery'
import StreamThumbnail from '@/components/StreamThumbnail'
import StreamGridSkeleton from '@/components/streams/StreamGridSkeleton'
import ErrorDisplay from '@/components/streams/ErrorDisplay'
import FiltersCard from '@/components/streams/FiltersCard'
import PaginationComponent from '@/components/streams/PaginationComponent'


const AllStreams = () => {
    const [
        offset,
        setOffset,
    ] = useState(0)
    const [
        selectedCreator,
        setSelectedCreator,
    ] = useState(null)
    const [
        selectedOrdering,
        setSelectedOrdering,
    ] = useState(null)

    // Use TanStack Query hooks for API calls
    const {
        data: streamsData,
        isLoading: streamsLoading,
        error: streamsError,
        refetch: refetchStreams,
    } = useStreams(selectedCreator?.value || -1, offset)

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

    /**
     * Handles creator selection change
     * @param {object} selectedOption
     */
    const handleCreatorChange = useCallback(selectedOption => {
        setSelectedCreator(selectedOption)
        setOffset(0) // Reset to first page when filtering
    }, [
    ])

    /**
     * Handles ordering selection change
     * @param {object} selectedOption
     */
    const handleOrderingChange = useCallback(selectedOption => {
        setSelectedOrdering(selectedOption)
    }, [
    ])

    // Calculate pages count with memoization
    const pagesCount = useMemo(() => Math.floor(maxOffset / 20), [
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
                selectedCreator={selectedCreator}
                onCreatorChange={handleCreatorChange}
                selectedOrdering={selectedOrdering}
                onOrderingChange={handleOrderingChange}
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
