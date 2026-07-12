'use client'
import { Card } from 'react-bootstrap'
import { useStreamReport } from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

/** Local naive "YYYY-MM-DDTHH:MM:SS" -> "HH:MM" without timezone drift. */
const clock = ts => (typeof ts === 'string' && ts.length >= 16 ? ts.slice(11, 16) : '--')

/** Render a number with thousands separators (integers). */
const num = value => Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 0,
})

/** Render a number with exactly one decimal place. */
const dec1 = value => Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
})

/** Format a 0..1 share as "XX.X%". */
const pct = value => `${dec1(value * 100)}%`

/**
 * Delta chip for a metric: signed percentage vs the baseline median with a
 * direction arrow. Only rendered when deltaPct is non-null (nullable = unknown).
 * @param {object} props
 * @param {number} props.deltaPct - rounded delta percentage vs baseline median
 */
const DeltaChip = ({ deltaPct }) => {
    const direction = deltaPct > 0 ? 'up' : deltaPct < 0 ? 'down' : 'flat'
    const icon = {
        up: 'bi-arrow-up-right',
        down: 'bi-arrow-down-right',
        flat: 'bi-dash',
    }[direction]
    const text = `${deltaPct > 0 ? '+' : ''}${dec1(deltaPct)}%`
    return (
        <span
            className={`report-delta is-${direction}`}
            aria-label={`${text} vs baseline median`}>
            <i
                className={`bi ${icon}`}
                aria-hidden="true" />
            {text}
        </span>
    )
}

/**
 * Stream report card: the rollup metrics as stat tiles, each annotated with a
 * delta chip and percentile hint against the creator's previous streams, plus
 * a highlights row (top emote / top phrase / top moments).
 *
 * Nullable = unknown contract: tiles with a null value are omitted entirely,
 * delta/percentile hints are hidden when the baseline is too small (< 2
 * rolled-up previous streams), and highlight chips are hidden when null/empty.
 * When nothing is computed yet a single muted hint is shown instead, so the
 * page still renders without rollups.
 *
 * @param {object} props
 * @param {string|number} props.streamId
 */
const StreamReportCard = ({ streamId }) => {
    const {
        data,
        isLoading,
        error,
        refetch,
    } = useStreamReport(streamId)

    if (isLoading) {
        return (
            <Card className="stream-report">
                <Card.Body>
                    <h3 className="section-label mb-3">Report card</h3>
                    <LoadingSpinner
                        size="md"
                        text="Loading report..."
                    />
                </Card.Body>
            </Card>
        )
    }

    if (error) {
        return (
            <Card className="stream-report">
                <Card.Body>
                    <h3 className="section-label mb-3">Report card</h3>
                    <ErrorAlert
                        error={error}
                        title="Failed to load report"
                        onRetry={refetch}
                        showDetails={process.env.NODE_ENV === 'development'}
                    />
                </Card.Body>
            </Card>
        )
    }

    const metrics = data?.metrics || {
    }
    const baselineCount = data?.baselineCount ?? 0

    const tileDefs = [
        {
            key: 'totalMessages',
            label: 'Total messages',
            format: num,
            phosphor: true,
        },
        {
            key: 'messagesPerMinute',
            label: 'Messages / min',
            format: dec1,
        },
        {
            key: 'uniqueChatters',
            label: 'Unique chatters',
            format: num,
        },
        {
            key: 'peakMessages',
            label: 'Peak minute',
            format: num,
            extraHint: data?.peakBucketMinute ? `at ${clock(data.peakBucketMinute)}` : null,
        },
        {
            key: 'newChatters',
            label: 'New chatters',
            format: num,
        },
        {
            key: 'returningChatters',
            label: 'Returning chatters',
            format: num,
        },
        {
            key: 'subShare',
            label: 'Sub share',
            format: pct,
        },
        {
            key: 'avgViewers',
            label: 'Avg viewers',
            format: num,
        },
        {
            key: 'peakViewers',
            label: 'Peak viewers',
            format: num,
            phosphor: true,
        },
    ]

    // Nullable = unknown: a null metric value means "not computed", so the tile
    // is omitted entirely rather than rendering a misleading 0 or bogus delta.
    const tiles = tileDefs
        .filter(def => metrics[def.key]?.value != null)
        .map(def => {
            const metric = metrics[def.key]
            const percentileHint = metric.percentile != null
                ? `P${dec1(metric.percentile)} · vs median ${def.format(metric.baselineMedian)}`
                : null
            return {
                ...def,
                value: def.format(metric.value),
                deltaPct: metric.deltaPct,
                hint: [
                    def.extraHint,
                    percentileHint,
                ].filter(Boolean).join(' · ') || null,
            }
        })

    const topEmote = data?.topEmote ?? null
    const topPhrase = data?.topPhrase ?? null
    const topMoments = data?.topMoments || []
    const hasHighlights = Boolean(topEmote || topPhrase || topMoments.length > 0)

    if (tiles.length === 0 && !hasHighlights) {
        return (
            <Card className="stream-report">
                <Card.Body>
                    <h3 className="section-label mb-3">Report card</h3>
                    <p className="stat-hint text-muted mb-0">
                        Metrics not yet computed for this stream.
                    </p>
                </Card.Body>
            </Card>
        )
    }

    return (
        <Card className="stream-report">
            <Card.Body>
                <h3 className="section-label mb-3">Report card</h3>

                {tiles.length > 0 && (
                    <div
                        className="stat-grid mb-0"
                        role="list"
                        aria-label="Stream report metrics">
                        {tiles.map(tile => (
                            <div
                                key={tile.label}
                                className="stat-tile"
                                role="listitem">
                                <div className="stat-label">{tile.label}</div>
                                <div className={`stat-value${tile.phosphor ? ' text-phosphor' : ''}`}>
                                    {tile.value}
                                    {tile.deltaPct != null && <DeltaChip deltaPct={tile.deltaPct} />}
                                </div>
                                {tile.hint ? <div className="stat-hint">{tile.hint}</div> : null}
                            </div>
                        ))}
                    </div>
                )}

                {(hasHighlights || baselineCount >= 2) && (
                    <div className="report-highlights">
                        {topEmote && (
                            <span className="report-chip">
                                <span className="report-chip-label">Top emote</span>
                                <span className="report-chip-value">{topEmote.name}</span>
                                <span className="report-chip-count mono">{num(topEmote.usageCount)}×</span>
                            </span>
                        )}
                        {topPhrase && (
                            <span className="report-chip">
                                <span className="report-chip-label">Top phrase</span>
                                <span className="report-chip-value">{topPhrase.phrase}</span>
                                <span className="report-chip-count mono">{num(topPhrase.usageCount)}×</span>
                            </span>
                        )}
                        {topMoments.map(moment => (
                            <span
                                key={moment.bucketMinute}
                                className="report-chip">
                                <span className="report-chip-label">Moment</span>
                                <span className="report-chip-value mono">{clock(moment.bucketMinute)}</span>
                                <span className="report-chip-count mono">
                                    {num(moment.messageCount)} msgs
                                </span>
                            </span>
                        ))}
                        {baselineCount >= 2 && (
                            <span className="stat-hint report-baseline-note">
                                vs previous {baselineCount} streams
                            </span>
                        )}
                    </div>
                )}
            </Card.Body>
        </Card>
    )
}

export default StreamReportCard
