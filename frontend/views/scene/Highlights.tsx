'use client'

import { useMemo, useState } from 'react'
import QueryState from '@/components/common/QueryState'
import EmptyState from '@/components/common/EmptyState'
import FilterPills from '@/components/common/FilterPills'
import HighlightCard from '@/components/scene/HighlightCard'
import {
    useSceneHighlights,
    type SceneHighlight,
} from '@/hooks/scene/useSceneHighlightsQueries'
import type { HighlightsSort, HighlightsWindow } from '@/lib/api/scene'

const PAGE_SIZE = 24

const WINDOW_TABS: Array<{ key: HighlightsWindow, label: string }> = [
    { key: 'all', label: 'All time' },
    { key: '7', label: '7 days' },
    { key: '30', label: '30 days' },
]

const SORT_TABS: Array<{ key: HighlightsSort, label: string }> = [
    { key: 'hype', label: 'Top hype' },
    { key: 'recent', label: 'Most recent' },
]

const Highlights = () => {
    const [windowKey, setWindowKey] = useState<HighlightsWindow>('all')
    const [sort, setSort] = useState<HighlightsSort>('hype')
    const query = useSceneHighlights({
        window: windowKey, sort, limit: PAGE_SIZE,
    })
    const accumulated = useMemo(
        () => query.data?.pages.flatMap(page => page.items) ?? [],
        [query.data],
    )
    const hasMore = Boolean(query.hasNextPage)
    const isFetchingMore = query.isFetchingNextPage
    const isFirstPageLoading = accumulated.length === 0 && query.isFetching && !query.isError
    const isRefetching = query.isFetching && !isFetchingMore && accumulated.length > 0

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">the scene&apos;s best chat moments</p>
                    <h1 className="page-title">Highlights</h1>
                </div>
            </div>

            <div
                className="toolbar highlights-toolbar"
                role="search"
                aria-label="Highlights filters">
                <FilterPills
                    options={WINDOW_TABS}
                    activeKey={windowKey}
                    ariaLabel="Time window"
                    onChange={setWindowKey}
                />
                <FilterPills
                    options={SORT_TABS}
                    activeKey={sort}
                    ariaLabel="Sort order"
                    onChange={setSort}
                />
            </div>

            <QueryState
                query={{
                    data: isFirstPageLoading ? undefined : accumulated,
                    error: query.error,
                    isLoading: isFirstPageLoading,
                    refetch: query.refetch,
                }}
                errorTitle="Failed to load highlights"
                loadingText="Surfacing the best moments…"
                loadingSize="md"
                isEmpty={(value: SceneHighlight[]) => value.length === 0}
                emptyState={(
                    <EmptyState title="No highlights yet">
                        No hype-worthy chat moments fall inside this window yet.
                    </EmptyState>
                )}
            >
                {(value: SceneHighlight[]) => (
                    <>
                        <div className={`highlight-grid${isRefetching ? ' is-refetching' : ''}`}>
                            {value.map(item => (
                                <HighlightCard
                                    key={`${item.streamId}:${item.offsetSeconds}`}
                                    highlight={item}
                                />
                            ))}
                        </div>
                        {hasMore ? (
                            <div className="highlight-load-more">
                                <button
                                    type="button"
                                    className="btn btn-outline-primary btn-sm"
                                    onClick={() => void query.fetchNextPage()}
                                    disabled={isFetchingMore}>
                                    {isFetchingMore ? 'Loading…' : 'Load more'}
                                </button>
                            </div>
                        ) : null}
                    </>
                )}
            </QueryState>
        </>
    )
}

export default Highlights
