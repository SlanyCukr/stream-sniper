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

/** Format a 0..1 share as "XX.X%", or null when it cannot be computed. */
const sharePct = (part, total) => {
    if (part == null || !total) {
        return null
    }
    return `${((part / total) * 100).toLocaleString(undefined, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
    })}%`
}

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

    // Nullable-column contract: unknown (null) != 0 — hide the tile entirely rather
    // than render a misleading 0 before the 0008 rollup / viewer backfill has run.
    if (metrics.peakViewers != null) {
        tiles.push({
            label: 'Peak viewers',
            value: num(metrics.peakViewers),
            phosphor: true,
        })
    }
    const subShare = sharePct(metrics.subMessages, metrics.totalMessages)
    if (subShare != null) {
        tiles.push({
            label: 'Sub share',
            value: subShare,
            hint: `${num(metrics.subMessages)} sub msgs`,
        })
    }
    const emoteShare = sharePct(metrics.emoteMessages, metrics.totalMessages)
    if (emoteShare != null) {
        tiles.push({
            label: 'Emote share',
            value: emoteShare,
            hint: `${num(metrics.emoteMessages)} emote msgs`,
        })
    }

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
