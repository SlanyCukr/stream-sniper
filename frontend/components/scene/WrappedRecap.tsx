'use client'

import Link from 'next/link'
import { formatCompactNumber, magnitudeBarWidth } from '@/utils/numberUtils'
import { formatStreamTimestamp } from '@/utils/dateUtils'
import StatusChip from '@/components/common/StatusChip'
import WrappedSection from '@/components/scene/WrappedSection'
import type { SceneWrapped } from '@/hooks/scene/useSceneWrappedQuery'

/** Compact count, or an em-dash when the metric is unknown (null). */
const compactOrDash = (value: number | null): string => (
    value == null ? '—' : formatCompactNumber(value)
)

const WrappedRecap = ({ wrapped }: { wrapped: SceneWrapped }) => {
    const {
        totals, topCreators, topChatters, topMoments, topCopypastas, topEmotes, notableEvents,
    } = wrapped

    const topCreatorMessages = topCreators.reduce((max, row) => Math.max(max, row.totalMessages), 0)
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
                    <div className="stat-tile">
                        <div className="stat-label">Creators</div>
                        <div className="stat-value">{formatCompactNumber(totals.creatorsActive)}</div>
                    </div>
                </div>
            </WrappedSection>

            {topCreators.length > 0 ? (
                <WrappedSection label="Top creators">
                    <div className="card card-hud">
                        <div className="wrapped-table-scroll" role="region" aria-label="Top creators">
                            <table className="table wrapped-table mb-0">
                                <thead>
                                    <tr>
                                        <th scope="col">#</th>
                                        <th scope="col">Creator</th>
                                        <th scope="col" className="text-end">Messages</th>
                                        <th scope="col" className="text-end">Streams</th>
                                        <th scope="col" className="text-end">Peak</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {topCreators.map(creator => (
                                        <tr key={creator.creatorId}>
                                            <td className="rank-num">{String(creator.rank).padStart(2, '0')}</td>
                                            <td>
                                                <Link className="wrapped-creator" href={`/creator/${creator.creatorId}`}>
                                                    {creator.profileImageUrl ? (
                                                        // eslint-disable-next-line @next/next/no-img-element
                                                        <img
                                                            className="scene-avatar"
                                                            src={creator.profileImageUrl}
                                                            alt=""
                                                            loading="lazy"
                                                        />
                                                    ) : (
                                                        <span className="scene-avatar scene-avatar-empty" aria-hidden="true" />
                                                    )}
                                                    <span className="wrapped-creator-name">{creator.displayName}</span>
                                                </Link>
                                            </td>
                                            <td className="wrapped-messages text-end">
                                                <span className="mono">{formatCompactNumber(creator.totalMessages)}</span>
                                                <span className="data-bar" aria-hidden="true">
                                                    <span
                                                        className="data-bar-fill"
                                                        style={{ width: `${magnitudeBarWidth(creator.totalMessages, topCreatorMessages)}%` }}
                                                    />
                                                </span>
                                            </td>
                                            <td className="mono text-end">{formatCompactNumber(creator.streams)}</td>
                                            <td className="mono text-end">{compactOrDash(creator.peakViewers)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </WrappedSection>
            ) : null}

            {topChatters.length > 0 ? (
                <WrappedSection label="Top chatters">
                    <ol className="rank-list wrapped-rank-list">
                        {topChatters.map(chatter => (
                            <li key={chatter.chatterId}>
                                <span className="rank">{String(chatter.rank).padStart(2, '0')}</span>
                                <Link className="nick" href={`/chatter/${chatter.chatterId}`}>{chatter.nick}</Link>
                                <span className="wrapped-home">
                                    {chatter.homeCreatorDisplayName ?? '—'}
                                </span>
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
                                    <div className="wrapped-moment-meta">
                                        <span className="wrapped-moment-creator">{moment.creatorDisplayName}</span>
                                        <Link
                                            className="wrapped-moment-title"
                                            href={`/stream/${moment.streamId}`}
                                            title={moment.streamTitle}
                                        >
                                            {moment.streamTitle}
                                        </Link>
                                    </div>
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
                                    <span className="pasta-chip pasta-chip-muted">
                                        {formatCompactNumber(pasta.creatorCount)}
                                        <span className="pasta-chip-unit"> channels</span>
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

            {notableEvents.length > 0 ? (
                <WrappedSection label="Notable events">
                    <ul className="wrapped-timeline">
                        {notableEvents.map((event, index) => (
                            <li className="wrapped-event" key={`${event.eventType}-${event.occurredAt}-${index}`}>
                                <time className="wrapped-event-when mono" dateTime={event.occurredAt}>
                                    {formatStreamTimestamp(event.occurredAt)}
                                </time>
                                <div className="wrapped-event-body">
                                    <p className="wrapped-event-title">{event.title}</p>
                                    <p className="wrapped-event-summary">{event.summary}</p>
                                    {event.creatorDisplayName ? (
                                        <span className="wrapped-event-creator">{event.creatorDisplayName}</span>
                                    ) : null}
                                </div>
                            </li>
                        ))}
                    </ul>
                </WrappedSection>
            ) : null}
        </div>
    )
}

export default WrappedRecap
