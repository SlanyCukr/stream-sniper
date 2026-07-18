'use client'

import { useEffect, useRef, useState } from 'react'
import QueryState from '@/components/common/QueryState'
import EmptyState from '@/components/common/EmptyState'
import FilterPills from '@/components/common/FilterPills'
import RankingsTable from '@/components/scene/RankingsTable'
import {
    useSceneRankings,
    type RankingsRow,
    type SceneRankings,
} from '@/hooks/scene/useSceneRankingsQueries'
import type { RankingsWindow } from '@/lib/api/scene'

const PAGE_SIZE = 25

const WINDOW_TABS: Array<{ key: RankingsWindow, label: string }> = [
    { key: 'all', label: 'All time' },
    { key: '7', label: '7 days' },
    { key: '30', label: '30 days' },
]

const Rankings = () => {
    const [activeWindow, setActiveWindow] = useState<RankingsWindow>('all')

    // Offset-based accumulation for "Load more" (append pages, reset on window switch).
    const [offset, setOffset] = useState(0)
    const [accumulated, setAccumulated] = useState<RankingsRow[]>([])
    const appendedOffsetRef = useRef(-1)

    const query = useSceneRankings({ window: activeWindow, limit: PAGE_SIZE, offset })

    // Reset accumulation synchronously WITH the window change (one batched render):
    // resetting in a useEffect instead fires a wasted query for the new window at
    // the old offset before the reset lands.
    const changeWindow = (key: RankingsWindow) => {
        if (key === activeWindow) return // re-clicking the active pill must not collapse loaded pages
        setActiveWindow(key)
        setOffset(0)
        setAccumulated([])
        appendedOffsetRef.current = -1
    }

    // Fold each freshly-arrived page into the accumulated list (skip stale placeholders).
    useEffect(() => {
        const data = query.data
        if (!data || query.isPlaceholderData) return
        if (offset === 0) {
            setAccumulated(data.items)
            appendedOffsetRef.current = 0
        } else if (appendedOffsetRef.current !== offset) {
            setAccumulated(prev => [...prev, ...data.items])
            appendedOffsetRef.current = offset
        }
    }, [query.data, query.isPlaceholderData, offset])

    const hasMore = Boolean(query.data?.hasMore)
    const isFetchingMore = offset > 0 && query.isFetching
    const loadMore = () => setOffset(current => current + PAGE_SIZE)

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
                    onChange={changeWindow}
                />
            </div>

            {accumulated.length > 0 ? (
                <RankingsTable
                    rows={accumulated}
                    hasMore={hasMore}
                    isFetchingMore={isFetchingMore}
                    onLoadMore={loadMore}
                />
            ) : (
                <QueryState
                    query={{
                        // Mask keepPreviousData during a window switch: the raw query
                        // still holds the OLD window's page (rows + hasMore), which
                        // would render stale rows with a live Load more that fires the
                        // new window at the old offset. Show the spinner instead.
                        data: query.isPlaceholderData ? undefined : query.data,
                        error: query.error,
                        isLoading: query.isLoading || query.isPlaceholderData,
                        refetch: query.refetch,
                    }}
                    errorTitle="Failed to load power rankings"
                    loadingText="Ranking the scene..."
                    isEmpty={(value: SceneRankings) => value.items.length === 0}
                    emptyState={(
                        <EmptyState title="No power rankings yet">
                            No chatter activity falls inside this window yet.
                        </EmptyState>
                    )}
                >
                    {(data: SceneRankings) => (
                        <RankingsTable
                            rows={data.items}
                            hasMore={data.hasMore}
                            isFetchingMore={isFetchingMore}
                            onLoadMore={loadMore}
                        />
                    )}
                </QueryState>
            )}
        </>
    )
}

export default Rankings
