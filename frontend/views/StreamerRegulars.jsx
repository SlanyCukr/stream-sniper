'use client'
import { useState, useCallback, useMemo } from 'react'
import Select from 'react-select'
import { useCreators } from '@/hooks/useApiQuery'
import TrendsPanel from '@/components/creator/TrendsPanel'
import RegularsPanel from '@/components/creator/RegularsPanel'
import ErrorAlert from '@/components/ErrorAlert'

const TABS = [
    {
        key: 'trends',
        label: 'Trends',
    },
    {
        key: 'regulars',
        label: 'Regulars',
    },
]

/**
 * Creator hub: one creator selector feeding two views of the same target —
 * "Trends" (per-stream engagement sparklines) and "Regulars" (recurring chatters).
 *
 * @param {object} props
 * @param {'trends'|'regulars'} [props.initialView] tab to open on first render
 *   (set from the `?view=` query; defaults to 'regulars')
 */
const StreamerRegulars = ({ initialView = 'regulars' }) => {
    const [
        selectedCreator,
        setSelectedCreator,
    ] = useState(null)
    const [
        view,
        setView,
    ] = useState(initialView === 'trends' ? 'trends' : 'regulars')

    const {
        data: creatorsData,
        error: creatorsError,
        refetch: refetchCreators,
    } = useCreators()

    const creatorId = selectedCreator?.value || null

    // Transform creators data for react-select with memoization
    const creators = useMemo(() => creatorsData?.map(creator => ({
        label: creator[1],
        value: creator[0],
    })) || [
    ], [
        creatorsData,
    ])

    const handleCreatorChange = useCallback(selectedOption => {
        setSelectedCreator(selectedOption)
    }, [
    ])

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Creators</h1>
                    <p className="page-sub">Per-stream trends and recurring chatters for a creator</p>
                </div>
            </div>

            {creatorsError && (
                <ErrorAlert
                    error={creatorsError}
                    title="Failed to load creators"
                    onRetry={refetchCreators}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            )}

            <div
                className="toolbar"
                role="search"
                aria-label="Creator selection">
                <span
                    className="toolbar-label"
                    aria-hidden="true">
                    Creator
                </span>
                <div className="toolbar-field">
                    <label
                        htmlFor="creator-hub-select"
                        className="visually-hidden"
                    >
                        Select a creator
                    </label>
                    <Select
                        classNamePrefix="rs"
                        instanceId="creator-hub-select"
                        inputId="creator-hub-select"
                        options={creators}
                        value={selectedCreator}
                        onChange={handleCreatorChange}
                        placeholder="Select creator..."
                        isClearable
                        aria-label="Select a creator"
                    />
                </div>
            </div>

            <div
                className="chatter-tabs"
                role="tablist"
                aria-label="Creator view"
            >
                {TABS.map(tab => (
                    <button
                        key={tab.key}
                        type="button"
                        role="tab"
                        id={`creator-tab-${tab.key}`}
                        aria-selected={view === tab.key}
                        aria-controls={`creator-panel-${tab.key}`}
                        className={view === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                        onClick={() => setView(tab.key)}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            <div
                id={`creator-panel-${view}`}
                role="tabpanel"
                aria-labelledby={`creator-tab-${view}`}
            >
                {view === 'trends'
                    ? <TrendsPanel creatorId={creatorId} />
                    : <RegularsPanel creatorId={creatorId} />}
            </div>
        </>
    )
}

export default StreamerRegulars
