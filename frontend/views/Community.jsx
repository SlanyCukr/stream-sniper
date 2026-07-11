'use client'
import { useState, useMemo, useCallback } from 'react'
import { Card } from 'react-bootstrap'
import { useCommunityOverlap } from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import OverlapMatrix from '@/components/community/OverlapMatrix'
import OverlapTable from '@/components/community/OverlapTable'
import NeighborsExplorer from '@/components/community/NeighborsExplorer'

const OVERLAP_LIMIT = 40

const METRIC_TABS = [
    {
        key: 'chatters',
        label: 'Chatters',
    },
    {
        key: 'regulars',
        label: 'Regulars',
    },
]

/**
 * Community overlap map: how the audiences of tracked creators intersect.
 * A single-hue Jaccard heatmap (with an accessible sortable table twin) plus an
 * "audience also watches" neighbor explorer, all driven by one metric toggle.
 */
const Community = () => {
    const [
        metric,
        setMetric,
    ] = useState('chatters')
    const [
        selectedPair,
        setSelectedPair,
    ] = useState(null)
    const [
        selectedCreator,
        setSelectedCreator,
    ] = useState(null)

    const {
        data,
        isLoading,
        error,
        refetch,
    } = useCommunityOverlap(OVERLAP_LIMIT, {
        placeholderData: previous => previous,
    })

    const creators = useMemo(() => data?.creators || [], [
        data,
    ])
    const pairs = useMemo(() => data?.pairs || [], [
        data,
    ])
    const computedAt = data?.computedAt || null
    const truncated = creators.length >= OVERLAP_LIMIT

    const nameMap = useMemo(() => {
        const map = new Map()
        creators.forEach(c => map.set(c.creatorId, c.displayName || c.nick || `#${c.creatorId}`))
        return map
    }, [
        creators,
    ])

    // Full both-metric readout for the selected pair (shown in the detail row).
    const selectedDetail = useMemo(() => {
        if (!selectedPair) {
            return null
        }
        const pair = pairs.find(p => p.a === selectedPair.aId && p.b === selectedPair.bId)
        if (!pair) {
            return null
        }
        return {
            aName: nameMap.get(pair.a) || `#${pair.a}`,
            bName: nameMap.get(pair.b) || `#${pair.b}`,
            sharedChatters: pair.sharedChatters,
            sharedRegulars: pair.sharedRegulars,
            jaccardChatters: pair.jaccardChatters,
            jaccardRegulars: pair.jaccardRegulars,
        }
    }, [
        selectedPair,
        pairs,
        nameMap,
    ])

    const handleSelectPair = useCallback(pair => setSelectedPair(pair), [
    ])

    const hasData = creators.length > 0 && pairs.length > 0

    const formatJaccard = value => (value == null ? '--' : `${(value * 100).toFixed(1)}%`)

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">audience intersection across tracked creators</p>
                    <h1 className="page-title">Community</h1>
                </div>
            </div>

            <div
                className="toolbar community-toolbar"
                aria-label="Overlap controls"
            >
                <span
                    className="toolbar-label"
                    aria-hidden="true"
                >
                    Metric
                </span>
                <div
                    className="chatter-tabs"
                    role="tablist"
                    aria-label="Overlap metric"
                >
                    {METRIC_TABS.map(tab => (
                        <button
                            key={tab.key}
                            type="button"
                            role="tab"
                            aria-selected={metric === tab.key}
                            className={metric === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                            onClick={() => setMetric(tab.key)}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
                {computedAt && (
                    <span className="toolbar-readout">
                        computed <strong>{new Date(computedAt).toLocaleString()}</strong>
                    </span>
                )}
                {truncated && (
                    <span className="toolbar-readout community-truncated">
                        top <strong>{OVERLAP_LIMIT}</strong> creators by audience
                    </span>
                )}
            </div>

            {error && (
                <ErrorAlert
                    error={error}
                    title="Failed to load community overlap"
                    onRetry={refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            )}

            {isLoading && !data && (
                <LoadingSpinner
                    size="lg"
                    text="Loading community overlap..."
                />
            )}

            {!isLoading && !error && !hasData && (
                <div className="empty-state">
                    <div
                        className="empty-scope"
                        aria-hidden="true"
                    />
                    <p className="empty-title">No overlap computed yet</p>
                    <p className="empty-hint">
                        Run the rollup backfill (<span className="mono">stream-sniper-rollup --all --force</span>)
                        to populate cross-creator audience overlap.
                    </p>
                </div>
            )}

            {hasData && (
                <div className={isLoading ? 'community-grid is-refetching' : 'community-grid'}>
                    <Card>
                        <Card.Body>
                            <span className="section-label">Overlap matrix</span>
                            <OverlapMatrix
                                creators={creators}
                                pairs={pairs}
                                metric={metric}
                                selectedPair={selectedPair}
                                onSelectPair={handleSelectPair}
                            />
                            {selectedDetail && (
                                <div className="overlap-detail">
                                    <span className="overlap-detail-pair">
                                        {selectedDetail.aName} <span aria-hidden="true">×</span> {selectedDetail.bName}
                                    </span>
                                    <span className="overlap-detail-metric">
                                        <span className="overlap-detail-key">shared chatters</span>
                                        <span className="mono">{selectedDetail.sharedChatters.toLocaleString()}</span>
                                    </span>
                                    <span className="overlap-detail-metric">
                                        <span className="overlap-detail-key">shared regulars</span>
                                        <span className="mono">{selectedDetail.sharedRegulars.toLocaleString()}</span>
                                    </span>
                                    <span className="overlap-detail-metric">
                                        <span className="overlap-detail-key">jaccard chatters</span>
                                        <span className="mono">{formatJaccard(selectedDetail.jaccardChatters)}</span>
                                    </span>
                                    <span className="overlap-detail-metric">
                                        <span className="overlap-detail-key">jaccard regulars</span>
                                        <span className="mono">{formatJaccard(selectedDetail.jaccardRegulars)}</span>
                                    </span>
                                </div>
                            )}
                        </Card.Body>
                    </Card>

                    <Card>
                        <Card.Body>
                            <span className="section-label">Overlap pairs</span>
                            <OverlapTable
                                creators={creators}
                                pairs={pairs}
                                metric={metric}
                                selectedPair={selectedPair}
                                onSelectPair={handleSelectPair}
                            />
                        </Card.Body>
                    </Card>

                    <Card>
                        <Card.Body>
                            <span className="section-label">Audience also watches</span>
                            <NeighborsExplorer
                                creators={creators}
                                metric={metric}
                                selected={selectedCreator}
                                onSelect={setSelectedCreator}
                            />
                        </Card.Body>
                    </Card>
                </div>
            )}
        </>
    )
}

export default Community
