'use client'

import { useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import Link from 'next/link'
import FilterPills from '@/components/common/FilterPills'
import QueryState from '@/components/common/QueryState'
import StatusChip from '@/components/common/StatusChip'
import { trendIndicator } from '@/components/scene/TrendingRow'
import {
    useSceneTrendingEmotes,
    type TrendingEmote,
} from '@/hooks/scene/useSceneTrendingQueries'
import type { TrendingWindow } from '@/lib/api/scene'
import { formatCompactNumber, magnitudeBarWidth } from '@/utils/numberUtils'
import { formatDate } from '@/utils/dateUtils'

const WINDOW_TABS: Array<{ key: TrendingWindow, label: string }> = [
    { key: 7, label: '7 days' },
    { key: 14, label: '14 days' },
    { key: 30, label: '30 days' },
]

// The trending endpoint's hard cap — the economy board wants the full field,
// not the compact top-20 the Trending page shows.
const BOARD_LIMIT = 50

const firstSeenLabel = (firstSeen: string | null): string => (
    firstSeen ? formatDate(firstSeen, 'MMM d, yyyy') : '—'
)

interface EmoteEconomyRowProps {
    rank: number
    item: TrendingEmote
    maxUsage: number
}

const EmoteEconomyRow = ({ rank, item, maxUsage }: EmoteEconomyRowProps) => {
    const indicator = trendIndicator(item.trend, item.deltaPct)
    const barStyle: CSSProperties = { width: `${magnitudeBarWidth(item.currentUsage, maxUsage)}%` }

    return (
        <tr>
            <td className="rank-num">{String(rank).padStart(2, '0')}</td>
            <td className="trending-primary">
                <Link className="trending-label" href={`/emotes/${item.emoteId}`}>{item.name}</Link>
                <span className="trending-source">{item.source}</span>
            </td>
            <td className="trending-usage text-end">
                <span className="mono trending-usage-now">{formatCompactNumber(item.currentUsage)}</span>
                <span className="data-bar" aria-hidden="true">
                    <span className="data-bar-fill" style={barStyle} />
                </span>
                <span className="mono trending-usage-prior">
                    was {formatCompactNumber(item.priorUsage)}
                </span>
            </td>
            <td className="trending-trend">
                <StatusChip variant={indicator.variant}>{indicator.label}</StatusChip>
            </td>
            <td className="mono text-end">{formatCompactNumber(item.creatorCount)}</td>
            <td className="mono text-end">{formatCompactNumber(item.chatterReach)}</td>
            <td className="emote-first-seen text-end">{firstSeenLabel(item.firstSeen)}</td>
        </tr>
    )
}

const EmoteEconomy = () => {
    const [windowDays, setWindowDays] = useState<TrendingWindow>(7)

    const emotesQuery = useSceneTrendingEmotes({ window: windowDays, limit: BOARD_LIMIT })

    // Keep `undefined` while pending so QueryState shows its spinner, not an empty board.
    const items = useMemo(
        () => (emotesQuery.data ? emotesQuery.data.items : undefined),
        [emotesQuery.data],
    )

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">who owns the scene&apos;s vocabulary</p>
                    <h1 className="page-title">Emote economy</h1>
                </div>
            </div>

            <div
                className="toolbar trending-toolbar"
                role="search"
                aria-label="Emote economy controls">
                <span className="toolbar-label">Window</span>
                <FilterPills
                    options={WINDOW_TABS}
                    activeKey={windowDays}
                    ariaLabel="Emote economy window"
                    onChange={setWindowDays}
                />
            </div>

            <section className="trending-board emote-economy-board card">
                <div className="trending-board-head">
                    <h2 className="trending-board-title">Scene-wide emote usage</h2>
                    <p className="emote-board-sub">
                        Usage vs. the prior {windowDays}-day window, with how many channels each emote crossed.
                    </p>
                </div>
                <QueryState
                    query={{
                        data: items,
                        isLoading: emotesQuery.isLoading,
                        error: emotesQuery.error,
                        refetch: emotesQuery.refetch,
                    }}
                    errorTitle="Unable to load the emote economy"
                    loadingText="Counting the scene's emotes…"
                    loadingSize="md"
                    isEmpty={(rows: TrendingEmote[]) => rows.length === 0}
                    emptyTitle="No emotes cleared the floor in this window"
                    emptyHint={`No emote hit meaningful usage across the scene in the last ${windowDays} days.`}
                >
                    {(rows: TrendingEmote[]) => {
                        const maxUsage = Math.max(1, ...rows.map(row => row.currentUsage))
                        return (
                            <div className="trending-table-wrap">
                                <table className="table trending-table emote-economy-table">
                                    <thead>
                                        <tr>
                                            <th className="trending-th-rank">#</th>
                                            <th>Emote</th>
                                            <th className="text-end">Now</th>
                                            <th>Trend</th>
                                            <th className="text-end">Channels</th>
                                            <th className="text-end">Reach</th>
                                            <th className="text-end">First seen</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rows.map((item, index) => (
                                            <EmoteEconomyRow
                                                key={item.emoteId}
                                                rank={index + 1}
                                                item={item}
                                                maxUsage={maxUsage}
                                            />
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )
                    }}
                </QueryState>
            </section>
        </>
    )
}

export default EmoteEconomy
