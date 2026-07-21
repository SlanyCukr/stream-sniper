'use client'

import Link from 'next/link'
import StatusChip from '@/components/common/StatusChip'
import { formatCompactNumber, magnitudeBarWidth } from '@/utils/numberUtils'
import WrappedSection from './WrappedSection'

interface RecapTotals {
    messages: number
    streams: number
    hoursStreamed: number | null
    activeChatters: number
    creatorsActive?: number
}

interface RecapChatter {
    rank: number
    chatterId: number
    nick: string
    totalMessages: number
    homeCreatorDisplayName?: string | null
}

interface RecapMoment {
    streamId: number
    streamTitle: string
    bucketMinute: string
    ratio: number | null
    messageCount: number
    creatorDisplayName?: string
}

interface RecapCopypasta {
    messageTextId: number
    text: string
    usageCount: number
    creatorCount?: number
}

interface RecapEmote {
    emoteId: number
    name: string
    source: string
    usage: number
}

const compactOrDash = (value: number | null): string => (
    value == null ? '—' : formatCompactNumber(value)
)

export const RecapTotalsSection = ({ totals }: { totals: RecapTotals }) => (
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
            {totals.creatorsActive !== undefined ? (
                <div className="stat-tile">
                    <div className="stat-label">Creators</div>
                    <div className="stat-value">{formatCompactNumber(totals.creatorsActive)}</div>
                </div>
            ) : null}
        </div>
    </WrappedSection>
)

export const RecapTopChattersSection = ({ chatters }: { chatters: RecapChatter[] }) => {
    if (chatters.length === 0) return null
    const topMessages = chatters.reduce((max, row) => Math.max(max, row.totalMessages), 0)

    return (
        <WrappedSection label="Top chatters">
            <ol className="rank-list wrapped-rank-list">
                {chatters.map(chatter => (
                    <li key={chatter.chatterId}>
                        <span className="rank">{String(chatter.rank).padStart(2, '0')}</span>
                        <Link className="nick" href={`/chatter/${chatter.chatterId}`}>{chatter.nick}</Link>
                        {chatter.homeCreatorDisplayName !== undefined ? (
                            <span className="wrapped-home">
                                {chatter.homeCreatorDisplayName ?? '—'}
                            </span>
                        ) : null}
                        <span className="count">
                            {formatCompactNumber(chatter.totalMessages)}
                            <span className="data-bar" aria-hidden="true">
                                <span
                                    className="data-bar-fill"
                                    style={{ width: `${magnitudeBarWidth(chatter.totalMessages, topMessages)}%` }}
                                />
                            </span>
                        </span>
                    </li>
                ))}
            </ol>
        </WrappedSection>
    )
}

export const RecapMomentsSection = ({ moments }: { moments: RecapMoment[] }) => {
    if (moments.length === 0) return null

    return (
        <WrappedSection label="Biggest moments">
            <div className="wrapped-moments">
                {moments.map(moment => (
                    <article
                        className="card card-hud wrapped-moment"
                        key={`${moment.streamId}-${moment.bucketMinute}`}
                    >
                        <header className="wrapped-moment-head">
                            <div className="wrapped-moment-meta">
                                {moment.creatorDisplayName !== undefined ? (
                                    <span className="wrapped-moment-creator">{moment.creatorDisplayName}</span>
                                ) : null}
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
    )
}

export const RecapCopypastasSection = ({ copypastas }: { copypastas: RecapCopypasta[] }) => {
    if (copypastas.length === 0) return null

    return (
        <WrappedSection label="Top copypastas">
            <ul className="wrapped-pastas">
                {copypastas.map(pasta => (
                    <li className="wrapped-pasta" key={pasta.messageTextId}>
                        <Link
                            className="wrapped-pasta-text"
                            href={`/copypasta/${pasta.messageTextId}`}
                            title={pasta.text}
                        >
                            {pasta.text}
                        </Link>
                        <span className="pasta-chips">
                            <span className="pasta-chip">
                                used
                                <span className="pasta-chip-unit">
                                    &times;{formatCompactNumber(pasta.usageCount)}
                                </span>
                            </span>
                            {pasta.creatorCount !== undefined ? (
                                <span className="pasta-chip pasta-chip-muted">
                                    {formatCompactNumber(pasta.creatorCount)}
                                    <span className="pasta-chip-unit"> channels</span>
                                </span>
                            ) : null}
                        </span>
                    </li>
                ))}
            </ul>
        </WrappedSection>
    )
}

export const RecapEmotesSection = ({ emotes }: { emotes: RecapEmote[] }) => {
    if (emotes.length === 0) return null
    const topUsage = emotes.reduce((max, row) => Math.max(max, row.usage), 0)

    return (
        <WrappedSection label="Top emotes">
            <ol className="rank-list wrapped-emotes">
                {emotes.map((emote, index) => (
                    <li key={emote.emoteId}>
                        <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                        <span className="nick">{emote.name}</span>
                        <StatusChip variant="neutral" className="wrapped-emote-source">
                            {emote.source}
                        </StatusChip>
                        <span className="count">
                            {formatCompactNumber(emote.usage)}
                            <span className="data-bar" aria-hidden="true">
                                <span
                                    className="data-bar-fill"
                                    style={{ width: `${magnitudeBarWidth(emote.usage, topUsage)}%` }}
                                />
                            </span>
                        </span>
                    </li>
                ))}
            </ol>
        </WrappedSection>
    )
}
