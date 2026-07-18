'use client'

import { useEffect, useRef, useState } from 'react'
import QueryState from '@/components/common/QueryState'
import EmptyState from '@/components/common/EmptyState'
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
    const [offset, setOffset] = useState(0)

    // Offset-based accumulation for "Load more": append each page, reset on filter change.
    const [accumulated, setAccumulated] = useState<SceneHighlight[]>([])
    const appendedOffsetRef = useRef(-1)

    const query = useSceneHighlights({
        window: windowKey, sort, limit: PAGE_SIZE, offset,
    })

    // Reset the accumulated window whenever the filter identity changes.
    useEffect(() => {
        setOffset(0)
        setAccumulated([])
        appendedOffsetRef.current = -1
    }, [windowKey, sort])

    // Fold each freshly-arrived page into the running list (skip placeholder frames).
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
    // First-load spinner (also filter switches): no rows yet AND still resolving.
    const isFirstPageLoading = accumulated.length === 0 && (query.isLoading || query.isFetching) && !query.isError
    const isRefetching = offset === 0 && query.isPlaceholderData && accumulated.length > 0

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
                <div className="chatter-tabs" role="tablist" aria-label="Time window">
                    {WINDOW_TABS.map(tab => (
                        <button
                            key={tab.key}
                            type="button"
                            role="tab"
                            aria-selected={windowKey === tab.key}
                            className={windowKey === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                            onClick={() => setWindowKey(tab.key)}>
                            {tab.label}
                        </button>
                    ))}
                </div>
                <div className="chatter-tabs" role="tablist" aria-label="Sort order">
                    {SORT_TABS.map(tab => (
                        <button
                            key={tab.key}
                            type="button"
                            role="tab"
                            aria-selected={sort === tab.key}
                            className={sort === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                            onClick={() => setSort(tab.key)}>
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            <QueryState
                query={{
                    data: isFirstPageLoading ? undefined : accumulated,
                    error: query.error,
                    isLoading: query.isLoading,
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
                                    onClick={() => setOffset(current => current + PAGE_SIZE)}
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
