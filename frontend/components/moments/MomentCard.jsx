'use client'
import Link from 'next/link'
import { vodDeepLink } from '@/utils/chatRender'
import { formatTimeAgo } from '@/utils/dateUtils'
import MomentReviewControls from './MomentReviewControls'
import ErrorAlert from '@/components/common/error/ErrorAlert'

const clock = timestamp => (
    typeof timestamp === 'string' && timestamp.length >= 16
        ? timestamp.slice(11, 16)
        : ''
)

const sharePct = value => (
    value == null ? null : `${Math.round(value * 100)}%`
)

const statusClass = status => {
    if (status === 'bookmarked' || status === 'clipped' || status === 'published') {
        return 'status-chip is-ok'
    }
    if (status === 'rejected') {
        return 'status-chip is-warn'
    }
    return 'status-chip'
}

const MomentCard = ({
    moment,
    isAdmin,
    pending,
    reviewError = null,
    onDismissReviewError = undefined,
    onReview,
}) => {
    const {
        streamId,
        streamTitle,
        streamStart,
        twitchVodId,
        creatorName,
        t,
        count,
        baseline,
        score,
        unique,
        subShare,
        emoteShare,
        topPhrases,
        sampleMessages,
        status,
        clipUrl,
        note,
    } = moment
    const vodHref = vodDeepLink(twitchVodId, streamStart, t)
    const topPhrase = topPhrases?.[0] || null
    const sample = sampleMessages?.[0] || null
    const subLabel = sharePct(subShare)
    const emoteLabel = sharePct(emoteShare)
    const reviewStatus = status || 'pending'

    return (
        <article className="moment-card">
            <header className="moment-card-head">
                <div className="moment-when">
                    <span className="moment-clock mono">{clock(t)}</span>
                    <span className="moment-ago">{formatTimeAgo(streamStart)}</span>
                </div>
                <span className={statusClass(status)} aria-label={`Review status: ${reviewStatus}`}>
                    {reviewStatus}
                </span>
            </header>

            <div className="moment-meta">
                <span className="moment-creator">{creatorName || 'Unknown creator'}</span>
                <Link
                    className="moment-title"
                    href={`/stream/${streamId}`}
                    title={streamTitle || `Stream ${streamId}`}>
                    {streamTitle || `Stream ${streamId}`}
                </Link>
            </div>

            <div className="moment-stats">
                {score != null ? (
                    <span
                        className="moment-score mono text-phosphor"
                        title={`${count?.toLocaleString?.() ?? count} messages vs baseline ${baseline}`}>
                        {score}×<span className="moment-score-unit"> baseline</span>
                    </span>
                ) : null}
                <span className="moment-stat mono">
                    {(count || 0).toLocaleString()}<span className="moment-stat-unit"> msgs</span>
                </span>
                {unique != null ? (
                    <span className="moment-stat mono">
                        {unique.toLocaleString()}<span className="moment-stat-unit"> chatters</span>
                    </span>
                ) : null}
                {subLabel != null ? (
                    <span className="moment-stat mono">{subLabel}<span className="moment-stat-unit"> subs</span></span>
                ) : null}
                {emoteLabel != null ? (
                    <span className="moment-stat mono">{emoteLabel}<span className="moment-stat-unit"> emote</span></span>
                ) : null}
            </div>

            {topPhrase ? (
                <div className="moment-phrase">
                    <span className="moment-phrase-chip">{topPhrase.phrase}</span>
                    {topPhrase.count ? <span className="moment-phrase-count mono">×{topPhrase.count.toLocaleString()}</span> : null}
                </div>
            ) : null}
            {sample ? (
                <p className="moment-sample" title={sample.text}>
                    <span aria-hidden="true">“</span>{sample.text}<span aria-hidden="true">”</span>
                    {sample.count > 1 ? <span className="moment-sample-count mono"> ×{sample.count.toLocaleString()}</span> : null}
                </p>
            ) : null}
            {clipUrl ? (
                <div className="moment-clip-result">
                    <a href={clipUrl} target="_blank" rel="noopener noreferrer">Watch clip</a>
                    {note ? <p>{note}</p> : null}
                </div>
            ) : null}

            <ErrorAlert
                error={reviewError}
                title="Unable to update highlight"
                onDismiss={onDismissReviewError}
                className="mt-3 mb-0" />

            <MomentReviewControls
                isAdmin={isAdmin}
                pending={pending}
                status={reviewStatus}
                clipUrl={clipUrl}
                note={note}
                vodHref={vodHref}
                onReview={onReview}
            />
        </article>
    )
}

export default MomentCard
