'use client'
import {
    useState, useCallback, useMemo,
} from 'react'
import {
    Card,
    CardGroup,
} from 'react-bootstrap'
import {
    useStreams, useCreators,
} from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import StreamThumbnail from '@/components/StreamThumbnail'
import ErrorDisplay from '@/components/streams/ErrorDisplay'
import FiltersCard from '@/components/streams/FiltersCard'
import PaginationComponent from '@/components/streams/PaginationComponent'
import { chunks } from '@/utils/utils'


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
            {isLoading && (
                <LoadingSpinner
                    size="lg"
                    text="Loading streams and creators..."
                    card
                />
            )}

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
            />

            <Card>
                <Card.Header>
                    <h1 id="streams-heading">All streams</h1>
                </Card.Header>
                <Card.Body>
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
                        {useMemo(() =>
                            chunks(streams, 4).map((chunk, chunkIndex) =>
                                <CardGroup
                                    key={chunkIndex}
                                    className="mb-4"
                                    role="group"
                                    aria-label={`Stream row ${chunkIndex + 1}`}
                                >
                                    {chunk.map((stream, streamIndex) =>
                                        <StreamThumbnail
                                            key={`${stream[0]}-${streamIndex}`}
                                            id={stream[0]}
                                            name={stream[1]}
                                            start={stream[2]}
                                            end={stream[3]}
                                            thumbnailSrc={stream[4]}
                                            messageCount={stream[5]}
                                        />,
                                    )}
                                </CardGroup>,
                            ), [
                            streams,
                        ],
                        )}
                        <PaginationComponent
                            pagesCount={pagesCount}
                            offset={offset}
                            updateOffset={updateOffset}
                        />
                    </div>
                </Card.Body>
            </Card>
        </>
    )
}

export default AllStreams
