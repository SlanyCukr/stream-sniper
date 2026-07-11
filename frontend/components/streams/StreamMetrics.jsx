'use client'
import { Card } from 'react-bootstrap'

/** Format a duration in seconds as "Hh Mm" / "Mm" / "--" when unknown. */
const formatDuration = seconds => {
    if (seconds == null) {
        return '--'
    }
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    return h > 0 ? `${h}h ${m}m` : `${m}m`
}

/** Local naive "YYYY-MM-DDTHH:MM:SS" -> "HH:MM" without timezone drift. */
const clock = ts => (typeof ts === 'string' && ts.length >= 16 ? ts.slice(11, 16) : '--')

/** Render a number with thousands separators, or a dash for null/undefined. */
const num = value => (value == null ? '--' : Number(value).toLocaleString())

/**
 * Stream rollup metrics as a grid of stat tiles. When `metrics` is null (the
 * rollup has not run for this stream yet) a single muted hint is shown instead,
 * so the page still renders without rollups.
 * @param {object} props
 * @param {object|null} props.metrics - camelCase metrics from useStreamTimeline
 */
const StreamMetrics = ({ metrics }) => {
    if (!metrics) {
        return (
            <Card className="stream-metrics">
                <Card.Body>
                    <p className="stat-hint text-muted mb-0">
                        Metrics not yet computed for this stream.
                    </p>
                </Card.Body>
            </Card>
        )
    }

    const tiles = [
        {
            label: 'Total messages',
            value: num(metrics.totalMessages),
            phosphor: true,
        },
        {
            label: 'Messages / min',
            value: metrics.msgsPerMin == null
                ? '--'
                : Number(metrics.msgsPerMin).toLocaleString(undefined, {
                    minimumFractionDigits: 1,
                    maximumFractionDigits: 1,
                }),
        },
        {
            label: 'Unique chatters',
            value: num(metrics.uniqueChatters),
        },
        {
            label: 'Peak minute',
            value: num(metrics.peakMessages),
            hint: metrics.peakAt ? `at ${clock(metrics.peakAt)}` : null,
        },
        {
            label: 'New chatters',
            value: num(metrics.newChatters),
        },
        {
            label: 'Returning chatters',
            value: num(metrics.returningChatters),
        },
        {
            label: 'Duration',
            value: formatDuration(metrics.durationSec),
        },
    ]

    return (
        <Card className="stream-metrics">
            <Card.Body>
                <div
                    className="stat-grid mb-0"
                    role="list"
                    aria-label="Stream metrics">
                    {tiles.map(tile => (
                        <div
                            key={tile.label}
                            className="stat-tile"
                            role="listitem">
                            <div className="stat-label">{tile.label}</div>
                            <div className={`stat-value${tile.phosphor ? ' text-phosphor' : ''}`}>
                                {tile.value}
                            </div>
                            {tile.hint ? <div className="stat-hint">{tile.hint}</div> : null}
                        </div>
                    ))}
                </div>
            </Card.Body>
        </Card>
    )
}

export default StreamMetrics
