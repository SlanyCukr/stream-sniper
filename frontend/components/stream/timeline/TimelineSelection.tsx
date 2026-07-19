'use client'
import { normalizeApiError } from '@/utils/errorUtils'
import StatusChip from '@/components/common/StatusChip'
import type { TimelineMoment } from '@/hooks/stream/timeline/useStreamTimelineQuery'
import type { useMomentReview } from '@/hooks/moments/useMomentsQueries'
import type { MomentReviewStatus } from '@/lib/api/moments'

type ReviewMutation = ReturnType<typeof useMomentReview>

// The timeline query mapper types topPhrases/sampleMessages as unknown[] |
// null (see useStreamTimelineQuery.ts), but the API actually returns these
// shapes (mirrored by the stricter scene.ts DTO for the same payload).
interface TimelinePhraseItem {
    phrase: string
    count: number
}

interface TimelineSampleItem {
    text: string
    count: number
}

const clock = (timestamp: string): string => typeof timestamp === 'string' && timestamp.length >= 16
    ? timestamp.slice(11, 16)
    : ''
const pct = (value: number): string => `${(value * 100).toLocaleString(undefined, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
})}%`

const TimelineShares = ({ moment }: { moment: TimelineMoment }) => {
    if (moment.subShare == null && moment.emoteShare == null) return null
    return (
        <div className="timeline-shares">
            {moment.subShare != null ? (
                <span className="timeline-share">
                    <span className="timeline-share-label">Sub share</span>
                    <span className="timeline-share-value">{pct(moment.subShare)}</span>
                </span>
            ) : null}
            {moment.emoteShare != null ? (
                <span className="timeline-share">
                    <span className="timeline-share-label">Emote share</span>
                    <span className="timeline-share-value">{pct(moment.emoteShare)}</span>
                </span>
            ) : null}
        </div>
    )
}

const TimelinePhrases = ({ phrases }: { phrases: TimelinePhraseItem[] }) => phrases.length ? (
    <div className="timeline-phrases">
        {phrases.map(phrase => (
            <span key={phrase.phrase} className="timeline-phrase-chip">
                {phrase.phrase}
                <span className="timeline-phrase-count">{(phrase.count || 0).toLocaleString()}</span>
            </span>
        ))}
    </div>
) : null

const TimelineSamples = ({ samples }: { samples: TimelineSampleItem[] }) => samples.length ? (
    <ul className="timeline-samples">
        {samples.map((sample, index) => (
            <li key={`${index}-${sample.text}`} className="timeline-sample">
                <span className="timeline-sample-text">{sample.text}</span>
                {sample.count > 1 ? (
                    <span className="timeline-sample-count">×{sample.count.toLocaleString()}</span>
                ) : null}
            </li>
        ))}
    </ul>
) : null

interface TimelineReviewActionsProps {
    moment: TimelineMoment
    reviewMutation: ReviewMutation
    onReview: (status: MomentReviewStatus | null) => void
}

const TimelineReviewActions = ({ moment, reviewMutation, onReview }: TimelineReviewActionsProps) => (
    <>
        <div className="timeline-review-actions">
            <button type="button" className={`timeline-review-btn${moment.status === 'bookmarked' ? ' is-active' : ''}`} disabled={reviewMutation.isPending} onClick={() => onReview('bookmarked')}>Bookmark</button>
            <button type="button" className={`timeline-review-btn timeline-review-btn--reject${moment.status === 'rejected' ? ' is-active' : ''}`} disabled={reviewMutation.isPending} onClick={() => onReview('rejected')}>Reject</button>
            {moment.status ? <button type="button" className="timeline-review-btn timeline-review-btn--clear" disabled={reviewMutation.isPending} onClick={() => onReview(null)}>Clear</button> : null}
        </div>
        {reviewMutation.isError ? (
            <p className="timeline-review-error" role="alert">
                {normalizeApiError(reviewMutation.error, 'Review failed').message}
            </p>
        ) : null}
    </>
)

interface TimelineSelectionProps {
    activeMoment: TimelineMoment | null
    vodHref: string | null
    isAdmin: boolean
    reviewMutation: ReviewMutation
    onReview: (status: MomentReviewStatus | null) => void
}

const TimelineSelection = ({
    activeMoment,
    vodHref,
    isAdmin,
    reviewMutation,
    onReview,
}: TimelineSelectionProps) => {
    if (!activeMoment) return null
    const topPhrases = (activeMoment.topPhrases || []) as TimelinePhraseItem[]
    const sampleMessages = (activeMoment.sampleMessages || []) as TimelineSampleItem[]
    return (
        <div className="timeline-selection">
            <div className="timeline-selection-head">
                <span className="timeline-selection-label">
                    Jumped replay to {clock(activeMoment.t)}
                    {activeMoment.score ? ` · ${activeMoment.score}x baseline` : ''}
                </span>
                {activeMoment.status ? <StatusChip variant={activeMoment.status === 'rejected' ? 'err' : 'ok'}>{activeMoment.status}</StatusChip> : null}
                {vodHref ? <a className="timeline-vod-link" href={vodHref} target="_blank" rel="noopener noreferrer">Open on Twitch</a> : null}
            </div>
            <TimelineShares moment={activeMoment} />
            <TimelinePhrases phrases={topPhrases} />
            <TimelineSamples samples={sampleMessages} />
            {isAdmin && activeMoment.isPersisted ? (
                <TimelineReviewActions
                    moment={activeMoment}
                    reviewMutation={reviewMutation}
                    onReview={onReview} />
            ) : null}
        </div>
    )
}

export default TimelineSelection
