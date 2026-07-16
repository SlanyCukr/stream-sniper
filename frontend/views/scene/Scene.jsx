'use client'
import { useState } from 'react'
import { useSceneLeaderboard } from '@/hooks/scene/useSceneLiveQueries'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import SceneLeaderboardTable from '@/components/scene/SceneLeaderboardTable'

const WINDOW_TABS = [
    { key: 7, label: '7 days' },
    { key: 30, label: '30 days' },
]

const Scene = () => {
    const [windowDays, setWindowDays] = useState(7)
    const {
        data,
        isLoading,
        error,
        refetch,
    } = useSceneLeaderboard({ windowDays })
    const entries = data?.entries || []

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

            {error ? (
                <ErrorAlert
                    error={error}
                    title="Failed to load leaderboard"
                    onRetry={refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            ) : isLoading ? (
                <LoadingSpinner text="Ranking the scene..." centered />
            ) : entries.length === 0 ? (
                <div className="empty-state">
                    <span className="empty-scope" aria-hidden="true" />
                    <p className="empty-title">No streams in window</p>
                    <p className="empty-hint">
                        No captured streams fall inside the last {windowDays} days.
                    </p>
                </div>
            ) : (
                <SceneLeaderboardTable entries={entries} />
            )}
        </>
    )
}

export default Scene
