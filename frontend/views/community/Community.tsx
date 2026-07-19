'use client'
import { useState } from 'react'
import { useCommunityOverlap, type OverlapMetric } from '@/hooks/community/useCommunityQuery'
import type { SelectedPair } from '@/hooks/community/useOverlapModel'
import QueryState from '@/components/common/QueryState'
import CommunityOverlapPanels from '@/components/community/CommunityOverlapPanels'

const METRIC_TABS: Array<{ key: OverlapMetric, label: string }> = [
    { key: 'chatters', label: 'Chatters' },
    { key: 'regulars', label: 'Regulars' },
]

const Community = () => {
    const [metric, setMetric] = useState<OverlapMetric>('chatters')
    const [selectedPair, setSelectedPair] = useState<SelectedPair | null>(null)
    const query = useCommunityOverlap(
        { limit: 40 },
        { placeholderData: previous => previous },
    )
    const creators = query.data?.creators || []

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

            <QueryState
                query={query}
                errorTitle="Failed to load community overlap"
                loadingText="Loading community overlap..."
                isEmpty={value => !((value?.creators?.length > 0) && (value?.pairs?.length > 0))}
                emptyTitle="No overlap computed yet"
                emptyHint="Audience overlap hasn’t been computed yet. It’ll appear after the next analytics run."
            >
                {value => (
                    <CommunityOverlapPanels
                        creators={value.creators}
                        pairs={value.pairs}
                        metric={metric}
                        selectedPair={selectedPair}
                        onSelectPair={setSelectedPair}
                        isRefetching={query.isRefetching}
                    />
                )}
            </QueryState>
        </>
    )
}

export default Community
