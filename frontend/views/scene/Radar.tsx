'use client'

import QueryState from '@/components/common/QueryState'
import EmptyState from '@/components/common/EmptyState'
import RadarCard from '@/components/scene/RadarCard'
import { useSceneRadar, type SceneRadar } from '@/hooks/scene/useSceneRadarQuery'
import { formatStreamTimestamp } from '@/utils/dateUtils'

/**
 * Live Moment Radar: near-real-time chat velocity for every live channel. The
 * hook polls every 30s (mirroring Live Now); the backend already orders spiking
 * channels first, and this view preserves that order. A failed poll after data
 * exists keeps the last grid rather than blanking it.
 */
const Radar = () => {
    const query = useSceneRadar()
    const generatedAt = query.data?.generatedAt ?? null

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">chat velocity, right now</p>
                    <h1 className="page-title">Moment Radar</h1>
                </div>
                <span className="toolbar-readout radar-readout mono">
                    {generatedAt ? (
                        <span className="radar-readout-time">{formatStreamTimestamp(generatedAt)}</span>
                    ) : null}
                    <span className="radar-readout-note">refreshes every 30s</span>
                </span>
            </div>

            <QueryState
                query={query}
                errorTitle="Failed to load the moment radar"
                loadingText="Tuning the radar..."
                loadingSize="md"
                isEmpty={(value: SceneRadar) => value.channels.length === 0}
                emptyState={(
                    <EmptyState title="No one is live right now">
                        the radar lights up when a tracked channel goes live
                    </EmptyState>
                )}
            >
                {(data: SceneRadar) => (
                    <div className="live-grid radar-grid">
                        {data.channels.map(channel => (
                            <RadarCard
                                key={channel.streamId}
                                channel={channel} />
                        ))}
                    </div>
                )}
            </QueryState>
        </>
    )
}

export default Radar
