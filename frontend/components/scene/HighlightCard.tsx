'use client'

import Link from 'next/link'
import { vodDeepLink } from '@/utils/chatRender'
import { formatCompactNumber } from '@/utils/numberUtils'
import { formatStreamTimestamp } from '@/utils/dateUtils'
import StatusChip from '@/components/common/StatusChip'
import type { SceneHighlight } from '@/hooks/scene/useSceneHighlightsQueries'

const MAX_PHRASES = 3
const MAX_SAMPLES = 2

/** Zero-epoch anchor so vodDeepLink's (moment - start) arithmetic yields offset. */
const EPOCH_ISO = new Date(0).toISOString()

/**
 * Build a Twitch VOD deep-link seeked to a highlight's offset from stream start.
 * `vodDeepLink` derives the seek from `(momentTs - streamStart)` in seconds, so
 * anchoring the start at epoch 0 and the moment at `offsetSeconds` reproduces the
 * offset exactly. Returns null when there is no VOD id (mirrors MomentCard).
 */
export const highlightVodHref = (twitchId: string | null, offsetSeconds: number): string | null =>
    vodDeepLink(twitchId, EPOCH_ISO, new Date(offsetSeconds * 1000).toISOString())

/** @returns the StatusChip variant for a moment review status. */
const statusVariant = (status: string): 'ok' | 'warn' | 'neutral' => {
    if (status === 'bookmarked' || status === 'clipped' || status === 'published') return 'ok'
    if (status === 'rejected') return 'warn'
    return 'neutral'
}

/** Fractional share (0..1) -> "NN%", or null so the caller hides the element. */
const sharePct = (value: number | null): string | null => (
    value == null ? null : `${Math.round(value * 100)}%`
)

const HighlightCard = ({ highlight }: { highlight: SceneHighlight }) => {
    const {
        streamId,
        streamTitle,
        twitchId,
        creatorId,
        creatorDisplayName,
        bucketMinute,
        offsetSeconds,
        ratio,
        messageCount,
        uniqueChatters,
        subShare,
        emoteShare,
        topPhrases,
        sampleMessages,
        clipUrl,
        reviewStatus,
    } = highlight

    const vodHref = highlightVodHref(twitchId, offsetSeconds)
    const phrases = (topPhrases ?? []).slice(0, MAX_PHRASES)
    const samples = (sampleMessages ?? []).slice(0, MAX_SAMPLES)
    const subLabel = sharePct(subShare)
    const emoteLabel = sharePct(emoteShare)

    return (
        <article className="card card-hud highlight-card">
            <header className="highlight-card-head">
                <div className="highlight-meta">
                    <Link className="highlight-creator" href={`/creator/${creatorId}`}>
                        {creatorDisplayName}
                    </Link>
                    <Link
                        className="highlight-title"
                        href={`/stream/${streamId}`}
                        title={streamTitle}>
                        {streamTitle}
                    </Link>
                </div>
                {ratio != null ? (
                    <span
                        className="highlight-hype text-phosphor mono"
                        title="Chat hype multiplier versus the stream's baseline">
                        &times;{ratio.toFixed(1)}
                    </span>
                ) : null}
            </header>

            <time className="highlight-when mono" dateTime={bucketMinute}>
                {formatStreamTimestamp(bucketMinute)}
            </time>

            <div className="highlight-stats">
                <span className="highlight-stat mono">
                    {formatCompactNumber(messageCount)}
                    <span className="highlight-stat-unit"> msgs</span>
                </span>
                <span className="highlight-stat mono">
                    {formatCompactNumber(uniqueChatters)}
                    <span className="highlight-stat-unit"> chatters</span>
                </span>
                {subLabel != null ? (
                    <span className="highlight-stat mono">
                        {subLabel}
                        <span className="highlight-stat-unit"> subs</span>
                    </span>
                ) : null}
                {emoteLabel != null ? (
                    <span className="highlight-stat mono">
                        {emoteLabel}
                        <span className="highlight-stat-unit"> emote</span>
                    </span>
                ) : null}
            </div>

            {phrases.length > 0 ? (
                <div className="pasta-chips highlight-phrases">
                    {phrases.map(phrase => (
                        <span className="pasta-chip" key={phrase.phrase}>
                            {phrase.phrase}
                            <span className="pasta-chip-unit">&times;{formatCompactNumber(phrase.count)}</span>
                        </span>
                    ))}
                </div>
            ) : null}

            {samples.length > 0 ? (
                <div className="highlight-samples">
                    {samples.map((sample, index) => (
                        <p
                            className="highlight-sample"
                            key={`${sample.text}::${index}`}
                            title={sample.text}>
                            <span aria-hidden="true">&ldquo;</span>
                            {sample.text}
                            <span aria-hidden="true">&rdquo;</span>
                            {sample.count > 1 ? (
                                <span className="highlight-sample-count mono"> &times;{formatCompactNumber(sample.count)}</span>
                            ) : null}
                        </p>
                    ))}
                </div>
            ) : null}

            <footer className="highlight-actions">
                {vodHref ? (
                    <a
                        className="btn btn-outline-primary btn-sm"
                        href={vodHref}
                        target="_blank"
                        rel="noopener noreferrer">
                        Jump to VOD
                    </a>
                ) : null}
                {clipUrl ? (
                    <a
                        className="highlight-clip"
                        href={clipUrl}
                        target="_blank"
                        rel="noopener noreferrer">
                        Watch clip
                    </a>
                ) : null}
                {reviewStatus ? (
                    <StatusChip
                        variant={statusVariant(reviewStatus)}
                        aria-label={`Review status: ${reviewStatus}`}>
                        {reviewStatus}
                    </StatusChip>
                ) : null}
            </footer>
        </article>
    )
}

export default HighlightCard
