'use client'
import { useState } from 'react'
import Link from 'next/link'
import { vodDeepLink } from '@/utils/chatRender'
import { formatTimeAgo } from '@/utils/dateUtils'

/** Local naive "YYYY-MM-DDTHH:MM:SS" -> "HH:MM" without timezone drift. */
const clock = ts => (typeof ts === 'string' && ts.length >= 16 ? ts.slice(11, 16) : '')

/** Percent label for a 0..1 share, or null when the share is unknown. */
const sharePct = value =>
    (value === null || value === undefined ? null : `${Math.round(value * 100)}%`)

/**
 * One highlight-queue row: stream context, spike magnitude, an explanatory top
 * phrase + sample message, a VOD deep-link, and admin-gated review controls.
 * Nullable analytics fields are hidden (never rendered as 0) per the rollup
 * contract — a field is null until the rollup recomputes it.
 *
 * @param {object} props
 * @param {object} props.moment - mapped queue item from useMomentsQueue
 * @param {boolean} props.isAdmin - whether review controls are shown
 * @param {boolean} props.pending - true while this row's mutation is in flight
 * @param {function} props.onReview - (status|null) => void; sets or clears review
 */
const MomentCard = ({
    moment, isAdmin, pending, onReview,
}) => {
    const {
        streamId,
        streamTitle,
        streamStart,
        twitchId,
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

    const [showClipForm, setShowClipForm] = useState(false)
    const [draftClipUrl, setDraftClipUrl] = useState(clipUrl || '')
    const [draftNote, setDraftNote] = useState(note || '')

    const vodHref = vodDeepLink(twitchId, streamStart, t)
    const topPhrase = Array.isArray(topPhrases) && topPhrases.length ? topPhrases[0] : null
    const sample = Array.isArray(sampleMessages) && sampleMessages.length ? sampleMessages[0] : null
    const subLabel = sharePct(subShare)
    const emoteLabel = sharePct(emoteShare)

    const chipClass =
        status === 'bookmarked'
            ? 'status-chip is-ok'
            : status === 'clipped' || status === 'published'
                ? 'status-chip is-ok'
            : status === 'rejected'
                ? 'status-chip is-warn'
                : 'status-chip'
    const chipLabel = status || 'pending'

    return (
        <article className="moment-card">
            <header className="moment-card-head">
                <div className="moment-when">
                    <span className="moment-clock mono">{clock(t)}</span>
                    <span className="moment-ago">{formatTimeAgo(streamStart)}</span>
                </div>
                <span
                    className={chipClass}
                    aria-label={`Review status: ${chipLabel}`}>
                    {chipLabel}
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
                {score !== null && score !== undefined ? (
                    <span
                        className="moment-score mono text-phosphor"
                        title={`${count?.toLocaleString?.() ?? count} messages vs baseline ${baseline}`}>
                        {score}×
                        <span className="moment-score-unit"> baseline</span>
                    </span>
                ) : null}
                <span className="moment-stat mono">
                    {(count || 0).toLocaleString()}
                    <span className="moment-stat-unit"> msgs</span>
                </span>
                {unique !== null && unique !== undefined ? (
                    <span className="moment-stat mono">
                        {unique.toLocaleString()}
                        <span className="moment-stat-unit"> chatters</span>
                    </span>
                ) : null}
                {subLabel !== null ? (
                    <span className="moment-stat mono">
                        {subLabel}
                        <span className="moment-stat-unit"> subs</span>
                    </span>
                ) : null}
                {emoteLabel !== null ? (
                    <span className="moment-stat mono">
                        {emoteLabel}
                        <span className="moment-stat-unit"> emote</span>
                    </span>
                ) : null}
            </div>

            {topPhrase ? (
                <div className="moment-phrase">
                    <span className="moment-phrase-chip">{topPhrase.phrase}</span>
                    {topPhrase.count ? (
                        <span className="moment-phrase-count mono">×{topPhrase.count.toLocaleString()}</span>
                    ) : null}
                </div>
            ) : null}

            {sample ? (
                <p
                    className="moment-sample"
                    title={sample.text}>
                    <span aria-hidden="true">“</span>
                    {sample.text}
                    <span aria-hidden="true">”</span>
                    {sample.count > 1 ? (
                        <span className="moment-sample-count mono"> ×{sample.count.toLocaleString()}</span>
                    ) : null}
                </p>
            ) : null}

            {clipUrl ? (
                <div className="moment-clip-result">
                    <a href={clipUrl} target="_blank" rel="noopener noreferrer">Watch clip</a>
                    {note ? <p>{note}</p> : null}
                </div>
            ) : null}

            {isAdmin && showClipForm ? (
                <form className="moment-clip-form" onSubmit={event => {
                    event.preventDefault()
                    onReview('clipped', { clipUrl: draftClipUrl, note: draftNote })
                    setShowClipForm(false)
                }}>
                    <label>
                        Clip URL
                        <input
                            className="form-control form-control-sm"
                            type="url"
                            required
                            value={draftClipUrl}
                            onChange={event => setDraftClipUrl(event.target.value)}
                            placeholder="https://clips.twitch.tv/..."
                        />
                    </label>
                    <label>
                        Curator note
                        <textarea
                            className="form-control form-control-sm"
                            maxLength={500}
                            value={draftNote}
                            onChange={event => setDraftNote(event.target.value)}
                        />
                    </label>
                    <div>
                        <button className="btn btn-primary btn-sm" type="submit" disabled={pending}>Save clip</button>
                        <button className="btn btn-link btn-sm" type="button" onClick={() => setShowClipForm(false)}>Cancel</button>
                    </div>
                </form>
            ) : null}

            <footer className="moment-actions">
                {vodHref ? (
                    <a
                        className="moment-vod-link"
                        href={vodHref}
                        target="_blank"
                        rel="noopener noreferrer">
                        <i
                            className="bi bi-box-arrow-up-right"
                            aria-hidden="true" />
                        Open VOD
                    </a>
                ) : (
                    <span className="moment-vod-missing">No VOD</span>
                )}

                {isAdmin ? (
                    <div
                        className="moment-review"
                        role="group"
                        aria-label="Review actions">
                        <button
                            type="button"
                            className={`moment-review-btn${status === 'bookmarked' ? ' is-active-ok' : ''}`}
                            disabled={pending || status === 'bookmarked'}
                            onClick={() => onReview('bookmarked')}
                            title="Bookmark this moment">
                            <i
                                className="bi bi-bookmark-star"
                                aria-hidden="true" />
                            Bookmark
                        </button>
                        {(status === 'bookmarked' || status === 'clipped') ? (
                            <button
                                type="button"
                                className={`moment-review-btn${status === 'clipped' ? ' is-active-ok' : ''}`}
                                disabled={pending}
                                onClick={() => setShowClipForm(value => !value)}>
                                <i className="bi bi-camera-video" aria-hidden="true" />
                                {clipUrl ? 'Edit clip' : 'Attach clip'}
                            </button>
                        ) : null}
                        {status === 'clipped' ? (
                            <button
                                type="button"
                                className="moment-review-btn"
                                disabled={pending}
                                onClick={() => onReview('published', { clipUrl, note })}>
                                <i className="bi bi-send" aria-hidden="true" />
                                Publish
                            </button>
                        ) : null}
                        <button
                            type="button"
                            className={`moment-review-btn${status === 'rejected' ? ' is-active-warn' : ''}`}
                            disabled={pending || status === 'rejected'}
                            onClick={() => onReview('rejected')}
                            title="Reject this moment">
                            <i
                                className="bi bi-x-circle"
                                aria-hidden="true" />
                            Reject
                        </button>
                        {status !== 'pending' ? (
                            <button
                                type="button"
                                className="moment-review-btn"
                                disabled={pending}
                                onClick={() => onReview(null)}
                                title="Clear review">
                                <i
                                    className="bi bi-arrow-counterclockwise"
                                    aria-hidden="true" />
                                Clear
                            </button>
                        ) : null}
                    </div>
                ) : null}
            </footer>
        </article>
    )
}

export default MomentCard
