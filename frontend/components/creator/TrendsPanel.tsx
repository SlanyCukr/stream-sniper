'use client'
import type { ComponentType } from 'react'
import { useRouter } from 'next/navigation'
import { Card } from 'react-bootstrap'
import {
    useCreatorTrends, type CreatorTrendPoint,
} from '@/hooks/creator/useCreatorTrendsQuery'
import QueryState from '@/components/common/QueryState'
import CreatorPanelEmpty from './CreatorPanelEmpty'
import {
    AreaSpark, BarSpark, StackSpark, formatTrendDuration,
} from './TrendSparklines'

interface SparkComponentProps {
    streams: CreatorTrendPoint[]
    values: (number | null)[]
    onStreamSelect: (streamId: number) => void
    getStreamLabel: (stream: CreatorTrendPoint) => string
}

interface TrendMetric {
    label: string
    selectValue: (stream: CreatorTrendPoint) => number | null
    formatLatest: (value: number | null | undefined) => string
    sparkComponent: ComponentType<SparkComponentProps>
}

const TREND_METRICS: TrendMetric[] = [
    {
        label: 'Messages / min',
        selectValue: stream => stream.msgsPerMin,
        formatLatest: value => (value ?? 0).toLocaleString(),
        sparkComponent: AreaSpark,
    },
    {
        label: 'Unique chatters',
        selectValue: stream => stream.uniqueChatters,
        formatLatest: value => (value ?? 0).toLocaleString(),
        sparkComponent: BarSpark,
    },
    {
        label: 'Duration',
        selectValue: stream => stream.durationSec,
        formatLatest: formatTrendDuration,
        sparkComponent: BarSpark,
    },
]

interface TrendMetricCardProps {
    metric: TrendMetric
    streams: CreatorTrendPoint[]
    onStreamSelect: (streamId: number) => void
    getStreamLabel: (stream: CreatorTrendPoint) => string
}

const TrendMetricCard = ({
    metric, streams, onStreamSelect, getStreamLabel,
}: TrendMetricCardProps) => {
    const Spark = metric.sparkComponent
    const values = streams.map(metric.selectValue)
    return (
        <div className="trend-card">
            <div className="trend-card-head">
                <span className="trend-card-title">{metric.label}</span>
                <span className="trend-card-latest">{metric.formatLatest(values.at(-1))}</span>
            </div>
            <Spark
                streams={streams}
                values={values}
                onStreamSelect={onStreamSelect}
                getStreamLabel={getStreamLabel}
            />
        </div>
    )
}

interface TrendsPanelProps {
    creatorId: number | null
}

/**
 * Creator trends: small-multiple sparkline cards (msgs/min area, unique chatters,
 * duration, new-vs-returning stacked) across a creator's recent streams.
 */
const TrendsPanel = ({ creatorId }: TrendsPanelProps) => {
    const router = useRouter()

    // useCreatorTrends requires a number; the query is `enabled: Boolean(creatorId)`
    // internally, so a null creatorId here never actually fires a request.
    const query = useCreatorTrends(creatorId as number)

    const handleStreamSelect = (streamId: number) => {
        router.push(`/stream/${streamId}`)
    }

    const getStreamLabel = (stream: CreatorTrendPoint) => {
        const when = stream.start ? new Date(stream.start).toLocaleDateString() : ''
        return `${stream.title || 'Untitled stream'}${when ? ` — ${when}` : ''}`
    }

    if (!creatorId) {
        return (
            <CreatorPanelEmpty title="No creator selected">
                Select a creator to see per-stream engagement trends.
            </CreatorPanelEmpty>
        )
    }

    return (
        <QueryState
            query={query}
            loadingText="Loading trends..."
            errorTitle="Failed to load trends"
            isEmpty={data => (data.streams || []).length === 0}
            emptyState={(
                <CreatorPanelEmpty title="No streams captured">
                    No streams recorded for this creator yet.
                </CreatorPanelEmpty>
            )}
        >
            {data => {
                const streams = data.streams || []

                // Metrics come from the rollup engine. Before a backfill runs, every
                // rollup-derived field is 0/null — detect that and prompt a backfill
                // instead of drawing flat charts.
                const hasMetrics = streams.some(s => (
                    (s.msgsPerMin || 0) > 0
                    || (s.uniqueChatters || 0) > 0
                    || (s.newChatters || 0) > 0
                    || (s.returningChatters || 0) > 0
                    || s.durationSec != null
                ))

                if (!hasMetrics) {
                    return (
                        <Card>
                            <Card.Body className="p-0">
                                <div className="empty-state">
                                    <div
                                        className="empty-scope"
                                        aria-hidden="true" />
                                    <p className="empty-title">Metrics not yet computed</p>
                                    <p className="empty-hint">
                                        Trends for this creator haven’t been computed yet.
                                        They’ll appear after the next analytics run.
                                    </p>
                                </div>
                            </Card.Body>
                        </Card>
                    )
                }

                return (
                    <div
                        className="trend-cards"
                        role="group"
                        aria-label="Creator per-stream trends"
                    >
                        {TREND_METRICS.map(metric => (
                            <TrendMetricCard
                                key={metric.label}
                                metric={metric}
                                streams={streams}
                                onStreamSelect={handleStreamSelect}
                                getStreamLabel={getStreamLabel}
                            />
                        ))}

                        <div className="trend-card">
                            <div className="trend-card-head">
                                <span className="trend-card-title">New vs returning</span>
                            </div>
                            <StackSpark
                                streams={streams}
                                onStreamSelect={handleStreamSelect}
                                getStreamLabel={getStreamLabel}
                            />
                            <div
                                className="stack-legend"
                                aria-hidden="true"
                            >
                                <span className="legend-chip legend-chip--returning">Returning</span>
                                <span className="legend-chip legend-chip--new">New</span>
                            </div>
                        </div>
                    </div>
                )
            }}
        </QueryState>
    )
}

export default TrendsPanel
