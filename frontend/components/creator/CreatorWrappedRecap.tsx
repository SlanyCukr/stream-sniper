'use client'

import Link from 'next/link'
import { formatCompactNumber, magnitudeBarWidth } from '@/utils/numberUtils'
import StatusChip from '@/components/common/StatusChip'
import WrappedSection from '@/components/scene/WrappedSection'
import type { CreatorWrapped } from '@/hooks/creator/useCreatorWrappedQuery'

/** Compact count, or an em-dash when the metric is unknown (null). */
const compactOrDash = (value: number | null): string => (
    value == null ? '—' : formatCompactNumber(value)
)

/**
 * One creator's version of the Scene Wrapped recap layout. Reuses `WrappedSection`
 * and the `.stat-grid` / `.rank-list` / `.wrapped-moments` / `.wrapped-pastas` styling
 * from the scene recap rather than forking them; there is no top-creators table or
 * notable-events timeline here (both are scene-wide, not single-creator concepts), and
 * the chatter/moment/copypasta rows drop the fields that would be constant for one
 * creator (home channel, creator label, channel count).
 */
const CreatorWrappedRecap = ({ wrapped }: { wrapped: CreatorWrapped }) => {
    const {
        totals, topChatters, topMoments, topCopypastas, topEmotes,
    } = wrapped

    const topChatterMessages = topChatters.reduce((max, row) => Math.max(max, row.totalMessages), 0)
    const topEmoteUsage = topEmotes.reduce((max, row) => Math.max(max, row.usage), 0)

    return (
        <div className="wrapped-flow">
            <WrappedSection label="The window, in numbers">
                <div className="stat-grid">
                    <div className="stat-tile">
                        <div className="stat-label">Messages</div>
                        <div className="stat-value text-phosphor">{formatCompactNumber(totals.messages)}</div>
                    </div>
                    <div className="stat-tile">
                        <div className="stat-label">Streams</div>
                        <div className="stat-value">{formatCompactNumber(totals.streams)}</div>
                    </div>
                    <div className="stat-tile">
                        <div className="stat-label">Hours</div>
                        <div className="stat-value">{compactOrDash(totals.hoursStreamed)}</div>
                    </div>
                    <div className="stat-tile">
                        <div className="stat-label">Chatters</div>
                        <div className="stat-value">{formatCompactNumber(totals.activeChatters)}</div>
                    </div>
                </div>
            </WrappedSection>

            {topChatters.length > 0 ? (
                <WrappedSection label="Top chatters">
                    <ol className="rank-list wrapped-rank-list">
                        {topChatters.map(chatter => (
                            <li key={chatter.chatterId}>
                                <span className="rank">{String(chatter.rank).padStart(2, '0')}</span>
                                <Link className="nick" href={`/chatter/${chatter.chatterId}`}>{chatter.nick}</Link>
                                <span className="count">
                                    {formatCompactNumber(chatter.totalMessages)}
                                    <span className="data-bar" aria-hidden="true">
                                        <span
                                            className="data-bar-fill"
                                            style={{ width: `${magnitudeBarWidth(chatter.totalMessages, topChatterMessages)}%` }}
                                        />
                                    </span>
                                </span>
                            </li>
                        ))}
                    </ol>
                </WrappedSection>
            ) : null}

            {topMoments.length > 0 ? (
                <WrappedSection label="Biggest moments">
                    <div className="wrapped-moments">
                        {/* (streamId, bucketMinute) is the moment's real primary key — one
                            dominant stream can own several top moments, so streamId alone
                            would collide as a list key. */}
                        {topMoments.map(moment => (
                            <article
                                className="card card-hud wrapped-moment"
                                key={`${moment.streamId}-${moment.bucketMinute}`}
                            >
                                <header className="wrapped-moment-head">
                                    <Link
                                        className="wrapped-moment-title"
                                        href={`/stream/${moment.streamId}`}
                                        title={moment.streamTitle}
                                    >
                                        {moment.streamTitle}
                                    </Link>
                                    {moment.ratio != null ? (
                                        <span
                                            className="wrapped-moment-hype text-phosphor mono"
                                            title="Chat hype multiplier versus the stream baseline"
                                        >
                                            &times;{moment.ratio.toFixed(1)}
                                        </span>
                                    ) : null}
                                </header>
                                <span className="wrapped-moment-count mono">
                                    {formatCompactNumber(moment.messageCount)}
                                    <span className="wrapped-moment-unit"> msgs</span>
                                </span>
                            </article>
                        ))}
                    </div>
                </WrappedSection>
            ) : null}

            {topCopypastas.length > 0 ? (
                <WrappedSection label="Top copypastas">
                    <ul className="wrapped-pastas">
                        {topCopypastas.map(pasta => (
                            <li className="wrapped-pasta" key={pasta.messageTextId}>
                                <Link className="wrapped-pasta-text" href={`/copypasta/${pasta.messageTextId}`} title={pasta.text}>
                                    {pasta.text}
                                </Link>
                                <span className="pasta-chips">
                                    <span className="pasta-chip">
                                        used
                                        <span className="pasta-chip-unit">&times;{formatCompactNumber(pasta.usageCount)}</span>
                                    </span>
                                </span>
                            </li>
                        ))}
                    </ul>
                </WrappedSection>
            ) : null}

            {topEmotes.length > 0 ? (
                <WrappedSection label="Top emotes">
                    <ol className="rank-list wrapped-emotes">
                        {topEmotes.map((emote, index) => (
                            <li key={emote.emoteId}>
                                <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                                <span className="nick">{emote.name}</span>
                                <StatusChip variant="neutral" className="wrapped-emote-source">{emote.source}</StatusChip>
                                <span className="count">
                                    {formatCompactNumber(emote.usage)}
                                    <span className="data-bar" aria-hidden="true">
                                        <span
                                            className="data-bar-fill"
                                            style={{ width: `${magnitudeBarWidth(emote.usage, topEmoteUsage)}%` }}
                                        />
                                    </span>
                                </span>
                            </li>
                        ))}
                    </ol>
                </WrappedSection>
            ) : null}
        </div>
    )
}

export default CreatorWrappedRecap
