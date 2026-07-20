'use client'
import { useStreamsExplorerController } from '@/hooks/stream/list/useStreamsExplorerController'
import StreamThumbnail from '@/components/stream/list/StreamThumbnail'
import StreamGridSkeleton from '@/components/stream/list/StreamGridSkeleton'
import ErrorDisplay from '@/components/stream/list/ErrorDisplay'
import FiltersCard from '@/components/stream/list/FiltersCard'
import Pagination from '@/components/common/pagination/Pagination'
import EmptyState from '@/components/common/EmptyState'

const AllStreams = () => {
    const {
        errorDisplayProps,
        filtersCardProps,
        results,
    } = useStreamsExplorerController()
    const {
        streams, isLoading, pageIndex, pageCount, onPageChange,
    } = results

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 id="streams-heading" className="page-title">All streams</h1>
                    <p className="page-sub">Captured VODs · chat intelligence</p>
                </div>
            </div>

            <ErrorDisplay {...errorDisplayProps} />

            <FiltersCard {...filtersCardProps} />

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
                            ? `Showing ${streams.length} streams on page ${pageIndex + 1} of ${pageCount}`
                            : 'No streams found'
                        }
                    </div>

                    {streams.length === 0 ? (
                        <div className="card">
                            <EmptyState title="No streams in scope">
                                No captured streams match this filter yet. Streams appear here once the collector has processed a VOD.
                            </EmptyState>
                        </div>
                    ) : (
                        <div className="stream-grid">
                            {streams.map((stream, streamIndex) => (
                                <StreamThumbnail
                                    key={`${stream.streamId}-${streamIndex}`}
                                    id={stream.streamId}
                                    name={stream.creatorName}
                                    start={stream.start}
                                    end={stream.end}
                                    thumbnailSrc={stream.thumbnailUrl}
                                    messageCount={stream.messageCount}
                                />
                            ))}
                        </div>
                    )}

                    <Pagination
                        pageIndex={pageIndex}
                        pageCount={pageCount}
                        onPageChange={onPageChange}
                        ariaLabel="Streams pagination"
                    />
                </div>
            )}
        </>
    )
}

export default AllStreams
