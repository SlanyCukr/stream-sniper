'use client'

import { Card } from 'react-bootstrap'
import type { TimelineMetrics } from '@/hooks/stream/timeline/useStreamTimelineQuery'
import { buildStreamMetricTiles } from './streamMetricTiles'
import StreamMetricTile from './StreamMetricTile'

interface StreamMetricsProps {
    metrics: TimelineMetrics | null
}

const StreamMetrics = ({ metrics }: StreamMetricsProps) => (
    <Card className="stream-metrics">
        <Card.Body>
            {!metrics ? (
                <p className="stat-hint text-muted mb-0">Metrics not yet computed for this stream.</p>
            ) : (
                <div className="stat-grid mb-0" role="list" aria-label="Stream metrics">
                    {buildStreamMetricTiles(metrics).map(tile => (
                        <StreamMetricTile
                            key={tile.label}
                            label={tile.label}
                            value={tile.value}
                            phosphor={tile.phosphor}
                            hint={tile.hint}
                        />
                    ))}
                </div>
            )}
        </Card.Body>
    </Card>
)

export default StreamMetrics
