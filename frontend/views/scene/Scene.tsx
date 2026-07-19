'use client'
import { useState } from 'react'
import { useSceneLeaderboard } from '@/hooks/scene/useSceneLiveQueries'
import QueryState from '@/components/common/QueryState'
import SceneLeaderboardTable from '@/components/scene/SceneLeaderboardTable'

const WINDOW_TABS: { key: 7 | 30, label: string }[] = [
    { key: 7, label: '7 days' },
    { key: 30, label: '30 days' },
]

const Scene = () => {
    const [windowDays, setWindowDays] = useState<7 | 30>(7)
    const {
        data,
        isLoading,
        error,
        refetch,
    } = useSceneLeaderboard({ windowDays })

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Scene leaderboard</h1>
                    <p className="page-sub">Creators ranked by chat activity</p>
                </div>
            </div>

            <div
                className="toolbar scene-toolbar"
                role="search"
                aria-label="Leaderboard window">
                <div className="chatter-tabs" role="tablist" aria-label="Window">
                    {WINDOW_TABS.map(tab => (
                        <button
                            key={tab.key}
                            type="button"
                            role="tab"
                            aria-selected={windowDays === tab.key}
                            className={windowDays === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                            onClick={() => setWindowDays(tab.key)}>
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            <QueryState
                query={{
                    data, isLoading, error, refetch,
                }}
                errorTitle="Failed to load leaderboard"
                loadingText="Ranking the scene..."
                loadingSize="md"
                isEmpty={value => (value?.entries || []).length === 0}
                emptyTitle="No streams in window"
                emptyHint={`No captured streams fall inside the last ${windowDays} days.`}
            >
                {value => <SceneLeaderboardTable entries={value.entries} />}
            </QueryState>
        </>
    )
}

export default Scene
