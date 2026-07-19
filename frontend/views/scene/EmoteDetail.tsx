'use client'

import type { CSSProperties } from 'react'
import Link from 'next/link'
import QueryState from '@/components/common/QueryState'
import StatusChip from '@/components/common/StatusChip'
import {
    useEmoteDetail,
    type EmoteDetail as EmoteDetailData,
    type EmoteWeeklyUsage,
} from '@/hooks/scene/useEmoteDetailQuery'
import { formatCompactNumber, magnitudeBarWidth } from '@/utils/numberUtils'
import { formatDate } from '@/utils/dateUtils'

const dateLabel = (value: string | null, mask = 'MMM d, yyyy'): string => (
    value ? formatDate(value, mask) : '—'
)

/** Weekly bars keyed off the busiest week so the trend reads at a glance. */
const WeeklyTrend = ({ weeks }: { weeks: EmoteWeeklyUsage[] }) => {
    if (weeks.length === 0) {
        return <p className="emote-detail-quiet">No usage in the trailing 12 weeks.</p>
    }
    const peak = Math.max(1, ...weeks.map(week => week.usage))
    return (
        <ul className="emote-weeks" aria-label="Usage per week">
            {weeks.map(week => {
                const barStyle: CSSProperties = { width: `${magnitudeBarWidth(week.usage, peak)}%` }
                return (
                    <li key={week.weekStart} className="emote-week-row">
                        <span className="emote-week-label mono">{formatDate(week.weekStart, 'MMM d')}</span>
                        <span className="data-bar" aria-hidden="true">
                            <span className="data-bar-fill" style={barStyle} />
                        </span>
                        <span className="mono text-end">{formatCompactNumber(week.usage)}</span>
                    </li>
                )
            })}
        </ul>
    )
}

const EmoteDetailBody = ({ data }: { data: EmoteDetailData }) => {
    const maxCreatorUsage = Math.max(1, ...data.topCreators.map(row => row.usage))
    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">one emote, its whole story</p>
                    <h1 className="page-title emote-detail-title">
                        {data.meta.name}
                        <StatusChip variant="neutral">{data.meta.source}</StatusChip>
                    </h1>
                </div>
                <Link className="btn btn-outline-secondary btn-sm" href="/emotes">
                    ← Emote economy
                </Link>
            </div>

            <div className="emote-detail-tiles">
                <div className="stat-tile">
                    <div className="stat-label">Lifetime uses</div>
                    <div className="stat-value">{formatCompactNumber(data.totals.usage)}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">Reach</div>
                    <div className="stat-value">{formatCompactNumber(data.totals.chatterReach)}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">Streams</div>
                    <div className="stat-value">{formatCompactNumber(data.totals.streamCount)}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">Channels</div>
                    <div className="stat-value">{formatCompactNumber(data.totals.creatorCount)}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">First seen</div>
                    <div className="stat-value stat-value-date">{dateLabel(data.meta.firstSeen)}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">Last used</div>
                    <div className="stat-value stat-value-date">{dateLabel(data.totals.lastUsed)}</div>
                </div>
            </div>

            <div className="emote-detail-grid">
                <section className="card emote-detail-card">
                    <h2 className="section-label">Where it lives</h2>
                    {data.topCreators.length === 0 ? (
                        <p className="emote-detail-quiet">Not used in any tracked channel yet.</p>
                    ) : (
                        <table className="table emote-detail-table">
                            <thead>
                                <tr>
                                    <th>Channel</th>
                                    <th className="text-end">Uses</th>
                                    <th className="text-end">Streams</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.topCreators.map(row => {
                                    const barStyle: CSSProperties = {
                                        width: `${magnitudeBarWidth(row.usage, maxCreatorUsage)}%`,
                                    }
                                    return (
                                        <tr key={row.creatorId}>
                                            <td>
                                                <Link href={`/creator/${row.creatorId}`}>
                                                    {row.displayName || row.nick}
                                                </Link>
                                            </td>
                                            <td className="text-end">
                                                <span className="mono">{formatCompactNumber(row.usage)}</span>
                                                <span className="data-bar" aria-hidden="true">
                                                    <span className="data-bar-fill" style={barStyle} />
                                                </span>
                                            </td>
                                            <td className="mono text-end">{row.streamCount}</td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    )}
                </section>

                <section className="card emote-detail-card">
                    <h2 className="section-label">Last 12 weeks</h2>
                    <WeeklyTrend weeks={data.weeklyUsage} />
                </section>
            </div>

            <section className="card emote-detail-card">
                <h2 className="section-label">Recent streams</h2>
                {data.recentStreams.length === 0 ? (
                    <p className="emote-detail-quiet">No streams recorded for this emote yet.</p>
                ) : (
                    <table className="table emote-detail-table">
                        <thead>
                            <tr>
                                <th>Stream</th>
                                <th>Channel</th>
                                <th className="text-end">Date</th>
                                <th className="text-end">Uses</th>
                                <th className="text-end">Chatters</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.recentStreams.map(row => (
                                <tr key={row.streamId}>
                                    <td className="emote-detail-stream">
                                        <Link href={`/stream/${row.streamId}`}>
                                            {row.title || `Stream #${row.streamId}`}
                                        </Link>
                                    </td>
                                    <td>{row.creatorDisplayName || row.creatorNick}</td>
                                    <td className="mono text-end">{dateLabel(row.start, 'MMM d')}</td>
                                    <td className="mono text-end">{formatCompactNumber(row.usage)}</td>
                                    <td className="mono text-end">{formatCompactNumber(row.chatterCount)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>
        </>
    )
}

const EmoteDetail = ({ emoteId }: { emoteId: number }) => {
    const query = useEmoteDetail(emoteId)
    return (
        <QueryState
            query={query}
            errorTitle="Emote unavailable"
            loadingText="Tracing the emote…"
            emptyState={null}
            showErrorDetails={false}
        >
            {(data: EmoteDetailData) => <EmoteDetailBody data={data} />}
        </QueryState>
    )
}

export default EmoteDetail
