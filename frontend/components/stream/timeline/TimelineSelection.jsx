'use client'
import { normalizeApiError } from '@/utils/errorUtils'

const clock = timestamp => typeof timestamp === 'string' && timestamp.length >= 16
    ? timestamp.slice(11, 16)
    : ''
const pct = value => `${(value * 100).toLocaleString(undefined, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
})}%`

const TimelineShares = ({ moment }) => {
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

const TimelinePhrases = ({ phrases }) => phrases.length ? (
    <div className="timeline-phrases">
        {phrases.map(phrase => (
            <span key={phrase.phrase} className="timeline-phrase-chip">
                {phrase.phrase}
                <span className="timeline-phrase-count">{(phrase.count || 0).toLocaleString()}</span>
            </span>
        ))}
    </div>
) : null

const TimelineSamples = ({ samples }) => samples.length ? (
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

const TimelineReviewActions = ({ moment, reviewMutation, onReview }) => (
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

const TimelineSelection = ({
    activeMoment,
    vodHref,
    isAdmin,
    reviewMutation,
    onReview,
}) => {
    if (!activeMoment) return null
    const topPhrases = activeMoment.topPhrases || []
    const sampleMessages = activeMoment.sampleMessages || []
    return (
        <div className="timeline-selection">
            <div className="timeline-selection-head">
                <span className="timeline-selection-label">
                    Jumped replay to {clock(activeMoment.t)}
                    {activeMoment.score ? ` · ${activeMoment.score}x baseline` : ''}
                </span>
                {activeMoment.status ? <span className={`status-chip ${activeMoment.status === 'rejected' ? 'is-err' : 'is-ok'}`}>{activeMoment.status}</span> : null}
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
