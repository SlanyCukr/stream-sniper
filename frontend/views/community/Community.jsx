'use client'
import { useState } from 'react'
import { useCommunityOverlap } from '@/hooks/community/useCommunityQuery'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import CommunityOverlapPanels from '@/components/community/CommunityOverlapPanels'

const METRIC_TABS = [
    { key: 'chatters', label: 'Chatters' },
    { key: 'regulars', label: 'Regulars' },
]

const Community = () => {
    const [metric, setMetric] = useState('chatters')
    const [selectedPair, setSelectedPair] = useState(null)
    const query = useCommunityOverlap(
        { limit: 40 },
        { placeholderData: previous => previous },
    )
    const creators = query.data?.creators || []
    const pairs = query.data?.pairs || []
    const hasData = creators.length > 0 && pairs.length > 0

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">audience intersection across tracked creators</p>
                    <h1 className="page-title">Community</h1>
                </div>
            </div>

            <div className="toolbar community-toolbar" aria-label="Overlap controls">
                <span className="toolbar-label" aria-hidden="true">Metric</span>
                <div className="chatter-tabs" role="tablist" aria-label="Overlap metric">
                    {METRIC_TABS.map(tab => (
                        <button
                            key={tab.key}
                            type="button"
                            role="tab"
                            aria-selected={metric === tab.key}
                            className={metric === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                            onClick={() => setMetric(tab.key)}>
                            {tab.label}
                        </button>
                    ))}
                </div>
                {query.data?.computedAt ? (
                    <span className="toolbar-readout">
                        computed <strong>{new Date(query.data.computedAt).toLocaleString()}</strong>
                    </span>
                ) : null}
                {creators.length >= 40 ? (
                    <span className="toolbar-readout community-truncated">
                        top <strong>40</strong> creators by audience
                    </span>
                ) : null}
            </div>

            {query.error ? (
                <ErrorAlert
                    error={query.error}
                    title="Failed to load community overlap"
                    onRetry={query.refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            ) : null}
            {query.isLoading && !query.data ? (
                <LoadingSpinner size="lg" text="Loading community overlap..." />
            ) : null}
            {!query.isLoading && !query.error && !hasData ? (
                <div className="empty-state">
                    <div className="empty-scope" aria-hidden="true" />
                    <p className="empty-title">No overlap computed yet</p>
                    <p className="empty-hint">
                        Run the rollup backfill (<span className="mono">stream-sniper-rollup --all --force</span>)
                        to populate cross-creator audience overlap.
                    </p>
                </div>
            ) : null}
            {hasData ? (
                <CommunityOverlapPanels
                    creators={creators}
                    pairs={pairs}
                    metric={metric}
                    selectedPair={selectedPair}
                    onSelectPair={setSelectedPair}
                    isRefetching={query.isRefetching}
                />
            ) : null}
        </>
    )
}

export default Community
