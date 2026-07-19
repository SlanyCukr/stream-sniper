'use client'

import { useMemo, useState } from 'react'
import FilterPills from '@/components/common/FilterPills'
import {
    useSceneTrendingCopypastas,
    useSceneTrendingEmotes,
    type TrendingCopypasta,
    type TrendingEmote,
} from '@/hooks/scene/useSceneTrendingQueries'
import TrendingBoard from '@/components/scene/TrendingBoard'
import type { TrendingRowModel } from '@/components/scene/TrendingRow'
import type { TrendingWindow } from '@/lib/api/scene'

const WINDOW_TABS: Array<{ key: TrendingWindow, label: string }> = [
    { key: 7, label: '7 days' },
    { key: 14, label: '14 days' },
    { key: 30, label: '30 days' },
]

const toCopypastaRow = (item: TrendingCopypasta): TrendingRowModel => ({
    key: `copypasta-${item.messageTextId}`,
    label: item.text,
    href: `/copypasta/${item.messageTextId}`,
    source: null,
    currentUsage: item.currentUsage,
    priorUsage: item.priorUsage,
    deltaPct: item.deltaPct,
    trend: item.trend,
    context: [
        { label: 'streams', value: item.streamCount },
        { label: 'creators', value: item.creatorCount },
    ],
})

const toEmoteRow = (item: TrendingEmote): TrendingRowModel => ({
    key: `emote-${item.emoteId}`,
    label: item.name,
    href: null,
    source: item.source,
    currentUsage: item.currentUsage,
    priorUsage: item.priorUsage,
    deltaPct: item.deltaPct,
    trend: item.trend,
    context: [
        { label: 'channels', value: item.creatorCount },
        { label: 'reach', value: item.chatterReach },
    ],
})

const Trending = () => {
    const [windowDays, setWindowDays] = useState<TrendingWindow>(7)

    const copypastasQuery = useSceneTrendingCopypastas({ window: windowDays })
    const emotesQuery = useSceneTrendingEmotes({ window: windowDays })

    // Project to presentation rows only once real data lands; keep `undefined`
    // while pending so QueryState renders its spinner rather than an empty board.
    const copypastaRows = useMemo(
        () => (copypastasQuery.data ? copypastasQuery.data.items.map(toCopypastaRow) : undefined),
        [copypastasQuery.data],
    )
    const emoteRows = useMemo(
        () => (emotesQuery.data ? emotesQuery.data.items.map(toEmoteRow) : undefined),
        [emotesQuery.data],
    )

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">what&apos;s spiking in the scene</p>
                    <h1 className="page-title">Trending</h1>
                </div>
            </div>

            <div
                className="toolbar trending-toolbar"
                role="search"
                aria-label="Trending controls">
                <span className="toolbar-label">Window</span>
                <FilterPills
                    options={WINDOW_TABS}
                    activeKey={windowDays}
                    ariaLabel="Trending window"
                    onChange={setWindowDays}
                />
            </div>

            <div className="trending-boards">
                <TrendingBoard
                    title="Copypastas"
                    primaryHeader="Copypasta"
                    contextHeader="Spread"
                    query={{
                        data: copypastaRows,
                        isLoading: copypastasQuery.isLoading,
                        error: copypastasQuery.error,
                        refetch: copypastasQuery.refetch,
                    }}
                    loadingText="Measuring copypasta velocity…"
                    errorTitle="Unable to load trending copypastas"
                    emptyTitle="No trending copypastas in this window"
                    emptyHint={`Nothing is spiking across the scene in the last ${windowDays} days.`}
                />
                <TrendingBoard
                    title="Emotes"
                    primaryHeader="Emote"
                    contextHeader="Reach"
                    query={{
                        data: emoteRows,
                        isLoading: emotesQuery.isLoading,
                        error: emotesQuery.error,
                        refetch: emotesQuery.refetch,
                    }}
                    loadingText="Measuring emote velocity…"
                    errorTitle="Unable to load trending emotes"
                    emptyTitle="No trending emotes in this window"
                    emptyHint={`Nothing is spiking across the scene in the last ${windowDays} days.`}
                />
            </div>
        </>
    )
}

export default Trending
