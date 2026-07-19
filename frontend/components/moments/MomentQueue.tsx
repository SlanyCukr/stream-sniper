import MomentCard from './MomentCard'
import type { MomentReviewMetadata } from './MomentReviewControls'
import Pagination from '@/components/common/pagination/Pagination'
import type { MomentQueueItem } from '@/hooks/moments/useMomentsQueries'
import type { MomentReviewDto, MomentReviewStatus } from '@/lib/api/moments'

const EMPTY_HINT: Record<string, string> = {
    all: 'No highlights detected yet. Moments appear here after streams are processed.',
    pending: 'Nothing awaiting review — every surfaced moment has been triaged.',
    bookmarked: 'No bookmarked moments yet. Bookmark spikes worth clipping to collect them here.',
    rejected: 'No rejected moments.',
    clipped: 'No clips attached yet.',
    published: 'No published highlights yet.',
}

interface ReviewFailure {
    key: string
    error: unknown
}

interface MomentQueueProps {
    items: MomentQueueItem[]
    statusKey: string
    isPlaceholderData: boolean
    isAdmin: boolean
    pendingKey: string | null
    reviewFailure: ReviewFailure | null
    onDismissReviewError: () => void
    onReview: (
        moment: MomentQueueItem,
        nextStatus: MomentReviewStatus | null,
        metadata?: MomentReviewMetadata,
    ) => Promise<MomentReviewDto | void>
    pageIndex: number
    pageCount: number
    onPageChange: (pageIndex: number) => void
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
}: MomentQueueProps) => {
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
