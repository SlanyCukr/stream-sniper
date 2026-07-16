import MomentCard from './MomentCard'
import Pagination from '@/components/common/pagination/Pagination'

const EMPTY_HINT = {
    all: 'No chat spikes have been enriched yet. Run the rollup backfill to populate the queue.',
    pending: 'Nothing awaiting review — every surfaced moment has been triaged.',
    bookmarked: 'No bookmarked moments yet. Bookmark spikes worth clipping to collect them here.',
    rejected: 'No rejected moments.',
    clipped: 'No clips attached yet.',
    published: 'No published highlights yet.',
}

const MomentQueue = ({
    items,
    statusKey,
    isPlaceholderData,
    isAdmin,
    pendingKey,
    reviewFailure,
    onDismissReviewError,
    onReview,
    pageIndex,
    pageCount,
    onPageChange,
}) => {
    if (items.length === 0) {
        return (
            <div className="empty-state">
                <span className="empty-scope" aria-hidden="true" />
                <p className="empty-title">No moments</p>
                <p className="empty-hint">{EMPTY_HINT[statusKey]}</p>
            </div>
        )
    }

    return (
        <>
            <div
                className={`moment-queue${isPlaceholderData ? ' is-refetching' : ''}`}
                aria-busy={isPlaceholderData}>
                {items.map(moment => {
                    const key = `${moment.streamId}:${moment.t}`
                    return (
                        <MomentCard
                            key={key}
                            moment={moment}
                            isAdmin={isAdmin}
                            pending={pendingKey === key}
                            reviewError={reviewFailure?.key === key ? reviewFailure.error : null}
                            onDismissReviewError={onDismissReviewError}
                            onReview={(next, metadata) => onReview(moment, next, metadata)}
                        />
                    )
                })}
            </div>
            <Pagination
                pageIndex={pageIndex}
                pageCount={pageCount}
                onPageChange={onPageChange}
                ariaLabel="Highlight queue pagination"
            />
        </>
    )
}

export default MomentQueue
