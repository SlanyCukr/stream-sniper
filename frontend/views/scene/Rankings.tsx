'use client'

import { useMemo, useState } from 'react'
import QueryState from '@/components/common/QueryState'
import EmptyState from '@/components/common/EmptyState'
import FilterPills from '@/components/common/FilterPills'
import RankingsTable from '@/components/scene/RankingsTable'
import {
    useSceneRankings,
    type RankingsRow,
} from '@/hooks/scene/useSceneRankingsQueries'
import type { RankingsWindow } from '@/lib/models/sceneFilters'

const PAGE_SIZE = 25

const WINDOW_TABS: Array<{ key: RankingsWindow, label: string }> = [
    { key: 'all', label: 'All time' },
    { key: '7', label: '7 days' },
    { key: '30', label: '30 days' },
]

// Mirrors the stable archetype set backend/stream_sniper/application/chatters/archetypes.py
// emits. Hardcoded (like WINDOW_TABS above) rather than derived from loaded rows so the
// filter row stays stable as pages load instead of shifting chips in and out.
const ARCHETYPE_FILTERS: Array<{ key: string, label: string }> = [
    { key: 'loyalist', label: 'Loyalist' },
    { key: 'wanderer', label: 'Wanderer' },
    { key: 'marathoner', label: 'Marathoner' },
    { key: 'chatterbox', label: 'Chatterbox' },
    { key: 'veteran', label: 'Veteran' },
    { key: 'newcomer', label: 'Newcomer' },
]

const Rankings = () => {
    const [activeWindow, setActiveWindow] = useState<RankingsWindow>('all')

    const query = useSceneRankings({ window: activeWindow, limit: PAGE_SIZE })

    // Any-of archetype filter, applied client-side only — it never touches the
    // query key/offset, so toggling a chip re-filters already-loaded rows with
    // no extra network request. Empty set = no filter (show every loaded row).
    const [activeArchetypes, setActiveArchetypes] = useState<Set<string>>(new Set())
    const toggleArchetype = (key: string) => {
        setActiveArchetypes((prev) => {
            const next = new Set(prev)
            if (next.has(key)) next.delete(key)
            else next.add(key)
            return next
        })
    }

    const accumulated = useMemo(
        () => query.data?.pages.flatMap(page => page.items) ?? [],
        [query.data],
    )
    const displayedRows = useMemo(
        () => (
            activeArchetypes.size === 0
                ? accumulated
                : accumulated.filter(row => row.archetypes.some(badge => activeArchetypes.has(badge.key)))
        ),
        [accumulated, activeArchetypes],
    )
    const filterEmptyMessage = accumulated.length > 0 && displayedRows.length === 0
        ? 'No loaded chatters match the selected badges. Clear a filter or load more rows.'
        : undefined

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">who runs the scene</p>
                    <h1 className="page-title">Power rankings</h1>
                </div>
            </div>

            <div
                className="toolbar scene-toolbar"
                role="search"
                aria-label="Rankings window"
            >
                <FilterPills
                    options={WINDOW_TABS}
                    activeKey={activeWindow}
                    ariaLabel="Window"
                    onChange={setActiveWindow}
                />
            </div>

            <div className="chatter-tabs" role="group" aria-label="Filter by archetype">
                {ARCHETYPE_FILTERS.map(option => (
                    <button
                        key={option.key}
                        type="button"
                        aria-pressed={activeArchetypes.has(option.key)}
                        className={activeArchetypes.has(option.key) ? 'chatter-tab active' : 'chatter-tab'}
                        onClick={() => toggleArchetype(option.key)}
                    >
                        {option.label}
                    </button>
                ))}
            </div>

            <QueryState
                query={{
                    data: query.data ? displayedRows : undefined,
                    error: query.error,
                    isLoading: query.isLoading,
                    refetch: query.refetch,
                }}
                errorTitle="Failed to load power rankings"
                loadingText="Ranking the scene..."
                isEmpty={(rows: RankingsRow[]) => rows.length === 0 && accumulated.length === 0}
                emptyState={(
                    <EmptyState title="No power rankings yet">
                        No chatter activity falls inside this window yet.
                    </EmptyState>
                )}
            >
                {(rows: RankingsRow[]) => (
                    <RankingsTable
                        rows={rows}
                        hasMore={Boolean(query.hasNextPage)}
                        isFetchingMore={query.isFetchingNextPage}
                        onLoadMore={() => void query.fetchNextPage()}
                        filterEmptyMessage={filterEmptyMessage}
                    />
                )}
            </QueryState>
        </>
    )
}

export default Rankings
