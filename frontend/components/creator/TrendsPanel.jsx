'use client'
import { useMemo, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Card } from 'react-bootstrap'
import { useCreatorTrends } from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

// SVG viewbox geometry (all sparklines share it; width scales via CSS)
const W = 240
const H = 56
const PAD_X = 6
const PAD_TOP = 6
const PAD_BOT = 8

/** Even x position for stream index `i` of `n` points. */
const xFor = (i, n) => (n <= 1 ? W / 2 : PAD_X + (i * (W - 2 * PAD_X)) / (n - 1))

/** Format a duration in seconds as "Hh Mm" / "Mm". */
const formatDuration = seconds => {
    if (seconds == null) {
        return '--'
    }
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    return h > 0 ? `${h}h ${m}m` : `${m}m`
}

/**
 * Transparent per-stream hit columns overlaying a chart: the keyboard-accessible,
 * clickable target that deep-links each point to its stream.
 * @param {object} props
 * @param {Array} props.streams - stream trend points
 * @param {function} props.onNav - navigate handler (streamId) => void
 * @param {function} props.labelFor - (stream) => tooltip label
 */
const HitColumns = ({
    streams, onNav, labelFor,
}) => {
    const n = streams.length
    const colW = n <= 1 ? W - 2 * PAD_X : (W - 2 * PAD_X) / n
    return streams.map((s, i) => {
        const cx = xFor(i, n)
        const hitX = n <= 1 ? PAD_X : PAD_X + i * colW
        return (
            <g key={s.streamId}>
                <rect
                    className="spark-hit"
                    x={hitX}
                    y={0}
                    width={colW}
                    height={H}
                    role="link"
                    tabIndex={0}
                    aria-label={labelFor(s)}
                    onClick={() => onNav(s.streamId)}
                    onKeyDown={event => {
                        if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault()
                            onNav(s.streamId)
                        }
                    }}
                >
                    <title>{labelFor(s)}</title>
                </rect>
                <line
                    className="spark-hit-marker"
                    x1={cx}
                    y1={PAD_TOP - 4}
                    x2={cx}
                    y2={H}
                />
            </g>
        )
    })
}

/**
 * Single-series area sparkline. `values` entries of `null` are rendered as GAPS
 * (the line/fill break) rather than as zero.
 */
const AreaSpark = ({
    streams, values, onNav, labelFor,
}) => {
    const n = values.length
    const nums = values.filter(v => v != null)
    const max = Math.max(1, ...nums)
    const yFor = v => H - PAD_BOT - (v / max) * (H - PAD_TOP - PAD_BOT)

    // split into contiguous non-null segments so gaps break the path
    const segments = []
    let current = []
    values.forEach((v, i) => {
        if (v == null) {
            if (current.length) {
                segments.push(current)
            }
            current = []
        } else {
            current.push({
                x: xFor(i, n),
                y: yFor(v),
            })
        }
    })
    if (current.length) {
        segments.push(current)
    }

    return (
        <svg
            className="trend-spark"
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            aria-hidden="true"
        >
            {segments.map((seg, idx) => {
                const line = seg.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
                const area = seg.length > 1
                    ? `${line} L${seg[seg.length - 1].x},${H - PAD_BOT} L${seg[0].x},${H - PAD_BOT} Z`
                    : null
                return (
                    <g key={idx}>
                        {area && (
                            <path
                                className="spark-area-fill"
                                d={area}
                            />
                        )}
                        <path
                            className="spark-area-line"
                            d={line}
                        />
                    </g>
                )
            })}
            <HitColumns
                streams={streams}
                onNav={onNav}
                labelFor={labelFor}
            />
        </svg>
    )
}

/**
 * Single-series bar sparkline. `null` values render as GAPS (no bar), not zero.
 */
const BarSpark = ({
    streams, values, onNav, labelFor, className = 'spark-bar',
}) => {
    const n = values.length
    const nums = values.filter(v => v != null)
    const max = Math.max(1, ...nums)
    const slot = n <= 1 ? W - 2 * PAD_X : (W - 2 * PAD_X) / n
    const barW = Math.max(2, slot * 0.55)

    return (
        <svg
            className="trend-spark"
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            aria-hidden="true"
        >
            {values.map((v, i) => {
                if (v == null) {
                    return null
                }
                const cx = n <= 1 ? W / 2 : PAD_X + slot * i + slot / 2
                const h = (v / max) * (H - PAD_TOP - PAD_BOT)
                return (
                    <rect
                        key={streams[i].streamId}
                        className={className}
                        x={cx - barW / 2}
                        y={H - PAD_BOT - h}
                        width={barW}
                        height={Math.max(0.5, h)}
                    />
                )
            })}
            <HitColumns
                streams={streams}
                onNav={onNav}
                labelFor={labelFor}
            />
        </svg>
    )
}

/**
 * Two-series stacked mini bars: returning (phosphor) on the bottom, new (amber)
 * on top. Both null → gap.
 */
const StackSpark = ({
    streams, onNav, labelFor,
}) => {
    const n = streams.length
    const totals = streams.map(s => {
        const r = s.returningChatters
        const nw = s.newChatters
        if (r == null && nw == null) {
            return null
        }
        return (r || 0) + (nw || 0)
    })
    const max = Math.max(1, ...totals.filter(t => t != null))
    const slot = n <= 1 ? W - 2 * PAD_X : (W - 2 * PAD_X) / n
    const barW = Math.max(2, slot * 0.55)
    const scale = H - PAD_TOP - PAD_BOT

    return (
        <svg
            className="trend-spark"
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            aria-hidden="true"
        >
            {streams.map((s, i) => {
                if (totals[i] == null) {
                    return null
                }
                const cx = n <= 1 ? W / 2 : PAD_X + slot * i + slot / 2
                const returningH = ((s.returningChatters || 0) / max) * scale
                const newH = ((s.newChatters || 0) / max) * scale
                const baseY = H - PAD_BOT
                return (
                    <g key={s.streamId}>
                        <rect
                            className="spark-bar spark-bar--returning"
                            x={cx - barW / 2}
                            y={baseY - returningH}
                            width={barW}
                            height={Math.max(0, returningH)}
                        />
                        <rect
                            className="spark-bar spark-bar--new"
                            x={cx - barW / 2}
                            y={baseY - returningH - newH}
                            width={barW}
                            height={Math.max(0, newH)}
                        />
                    </g>
                )
            })}
            <HitColumns
                streams={streams}
                onNav={onNav}
                labelFor={labelFor}
            />
        </svg>
    )
}

/**
 * Creator trends: small-multiple sparkline cards (msgs/min area, unique chatters,
 * duration, new-vs-returning stacked) across a creator's recent streams.
 * @param {object} props
 * @param {number|null} props.creatorId
 */
const TrendsPanel = ({ creatorId }) => {
    const router = useRouter()

    const {
        data,
        isLoading,
        error,
        refetch,
    } = useCreatorTrends(creatorId)

    const streams = useMemo(() => data?.streams || [], [
        data,
    ])

    const onNav = useCallback(streamId => {
        router.push(`/stream/${streamId}`)
    }, [
        router,
    ])

    const labelFor = useCallback(s => {
        const when = s.start ? new Date(s.start).toLocaleDateString() : ''
        return `${s.title || 'Untitled stream'}${when ? ` — ${when}` : ''}`
    }, [
    ])

    if (!creatorId) {
        return (
            <Card>
                <Card.Body className="p-0">
                    <div className="empty-state">
                        <div
                            className="empty-scope"
                            aria-hidden="true" />
                        <p className="empty-title">No creator selected</p>
                        <p className="empty-hint">
                            Select a creator to see per-stream engagement trends.
                        </p>
                    </div>
                </Card.Body>
            </Card>
        )
    }

    if (isLoading) {
        return (
            <LoadingSpinner
                size="lg"
                text="Loading trends..."
            />
        )
    }

    if (error) {
        return (
            <ErrorAlert
                error={error}
                title="Failed to load trends"
                onRetry={refetch}
                showDetails={process.env.NODE_ENV === 'development'}
            />
        )
    }

    if (streams.length === 0) {
        return (
            <Card>
                <Card.Body className="p-0">
                    <div className="empty-state">
                        <div
                            className="empty-scope"
                            aria-hidden="true" />
                        <p className="empty-title">No streams captured</p>
                        <p className="empty-hint">No streams recorded for this creator yet.</p>
                    </div>
                </Card.Body>
            </Card>
        )
    }

    // Metrics come from the rollup engine. Before a backfill runs, every rollup-derived
    // field is 0/null — detect that and prompt a backfill instead of drawing flat charts.
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
                            Run the rollup backfill (<span className="mono">stream-sniper-rollup --all --force</span>)
                            to populate per-stream trends for this creator.
                        </p>
                    </div>
                </Card.Body>
            </Card>
        )
    }

    const latest = streams[streams.length - 1]

    return (
        <div
            className="trend-cards"
            role="group"
            aria-label="Creator per-stream trends"
        >
            <div className="trend-card">
                <div className="trend-card-head">
                    <span className="trend-card-title">Messages / min</span>
                    <span className="trend-card-latest">{(latest.msgsPerMin ?? 0).toLocaleString()}</span>
                </div>
                <AreaSpark
                    streams={streams}
                    values={streams.map(s => (s.msgsPerMin == null ? null : s.msgsPerMin))}
                    onNav={onNav}
                    labelFor={labelFor}
                />
            </div>

            <div className="trend-card">
                <div className="trend-card-head">
                    <span className="trend-card-title">Unique chatters</span>
                    <span className="trend-card-latest">{(latest.uniqueChatters ?? 0).toLocaleString()}</span>
                </div>
                <BarSpark
                    streams={streams}
                    values={streams.map(s => (s.uniqueChatters == null ? null : s.uniqueChatters))}
                    onNav={onNav}
                    labelFor={labelFor}
                />
            </div>

            <div className="trend-card">
                <div className="trend-card-head">
                    <span className="trend-card-title">Duration</span>
                    <span className="trend-card-latest">{formatDuration(latest.durationSec)}</span>
                </div>
                <BarSpark
                    streams={streams}
                    values={streams.map(s => (s.durationSec == null ? null : s.durationSec))}
                    onNav={onNav}
                    labelFor={labelFor}
                />
            </div>

            <div className="trend-card">
                <div className="trend-card-head">
                    <span className="trend-card-title">New vs returning</span>
                </div>
                <StackSpark
                    streams={streams}
                    onNav={onNav}
                    labelFor={labelFor}
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
}

export default TrendsPanel
