'use client'
import {
    useState,
    useMemo,
    useCallback,
} from 'react'
import { Card } from 'react-bootstrap'
import { vodDeepLink } from '@/utils/chatRender'
import { useAuth } from '@/contexts/AuthContext'
import { useMomentReview } from '@/hooks/useApiQuery'

// SVG geometry. preserveAspectRatio="none" stretches these units to the container
// box, so bars scale with width/height; text/markers live in the HTML overlay to
// avoid stroke/label distortion. The viewer lane shares the same 1000-wide x-grid
// as the message lane so the two small multiples stay vertically aligned.
const VW = 1000
const VH = 160
const VVH = 72

/** Local naive "YYYY-MM-DDTHH:MM:SS" -> "HH:MM" without timezone drift. */
const clock = ts => (typeof ts === 'string' && ts.length >= 16 ? ts.slice(11, 16) : '')

/** Format a 0..1 share as "XX.X%". Caller must skip null values. */
const pct = value => `${(value * 100).toLocaleString(undefined, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
})}%`

/**
 * Stream chat-activity timeline. Two aligned small multiples sharing one x-grid:
 * an inline-SVG messages-per-minute bar chart (phosphor) on top and, when viewer
 * samples exist, a viewer-count area/line lane ($sky) directly below with its own
 * y-scale. NO dual axis — each lane owns its scale. One shared hover drives a
 * crosshair across both lanes plus a combined tooltip. Amber spike markers are
 * focusable buttons; selecting one jumps the replay, reveals a VOD deep-link, and
 * (for admins) enriched moment review controls. Renders nothing when there are no
 * buckets, so the replay still works without rollups.
 *
 * @param {object} props
 * @param {object} props.timeline - mapped timeline: {streamId, streamStart, twitchId,
 *   buckets, moments, viewerSamples, peakViewers}
 * @param {function} props.onJump - (bucketMinuteIso) => void; jump the replay to a moment
 */
const StreamTimeline = ({ timeline, onJump }) => {
    const { isAdmin } = useAuth()
    const reviewMutation = useMomentReview()

    const [
        hoverIndex,
        setHoverIndex,
    ] = useState(null)
    const [
        selectedTs,
        setSelectedTs,
    ] = useState(null)

    const buckets = useMemo(() => timeline?.buckets || [], [
        timeline?.buckets,
    ])
    const moments = useMemo(() => timeline?.moments || [], [
        timeline?.moments,
    ])
    const viewerSamples = useMemo(() => timeline?.viewerSamples || [], [
        timeline?.viewerSamples,
    ])

    const n = buckets.length

    const maxCount = useMemo(
        () => Math.max(1, ...buckets.map(b => b.count || 0)),
        [
            buckets,
        ],
    )

    // Viewer lane geometry, aligned to the same per-minute x-grid as the bars. Each
    // sample is placed at the fractional bucket index for its timestamp, then mapped
    // to the bar-center x so the curve lines up with the columns above it. null when
    // there are no samples -> the lane (and its legend chip) is omitted entirely.
    const viewerLane = useMemo(() => {
        if (viewerSamples.length === 0 || n === 0) {
            return null
        }
        const first = Date.parse(buckets[0].t)
        const last = Date.parse(buckets[n - 1].t)
        const span = last - first
        const points = viewerSamples
            .map(s => {
                const at = Date.parse(s.t)
                const raw = span > 0 && Number.isFinite(at)
                    ? ((at - first) / span) * (n - 1)
                    : 0
                const idxFrac = Math.min(n - 1, Math.max(0, raw))
                return {
                    idxFrac,
                    viewers: s.viewerCount || 0,
                    x: ((idxFrac + 0.5) / n) * VW,
                }
            })
            .sort((a, b) => a.x - b.x)
        const maxViewers = Math.max(1, ...points.map(p => p.viewers))
        const y = v => VVH - (v / maxViewers) * VVH
        const line = points.map(p => `${p.x.toFixed(2)},${y(p.viewers).toFixed(2)}`).join(' ')
        const area = points.length
            ? `M ${points[0].x.toFixed(2)},${VVH} `
                + points.map(p => `L ${p.x.toFixed(2)},${y(p.viewers).toFixed(2)}`).join(' ')
                + ` L ${points[points.length - 1].x.toFixed(2)},${VVH} Z`
            : ''
        return {
            points,
            maxViewers,
            line,
            area,
        }
    }, [
        viewerSamples,
        buckets,
        n,
    ])

    // Marker x-position (percent of the plotting area) keyed to its bucket index;
    // falls back to the time fraction when a moment has no exact bucket match.
    const markerLeft = useCallback(momentTs => {
        if (n === 0) {
            return 0
        }
        const idx = buckets.findIndex(b => b.t === momentTs)
        if (idx >= 0) {
            return ((idx + 0.5) / n) * 100
        }
        const first = Date.parse(buckets[0].t)
        const last = Date.parse(buckets[n - 1].t)
        const at = Date.parse(momentTs)
        if (!Number.isFinite(at) || last <= first) {
            return 0
        }
        return Math.min(100, Math.max(0, ((at - first) / (last - first)) * 100))
    }, [
        buckets,
        n,
    ])

    // One shared hover: convert the pointer x within either lane's plotting box to a
    // bucket index. offsetX is relative to the SVG (== plotting area), so both lanes
    // resolve to the same index and drive a single crosshair + tooltip.
    const handleMove = useCallback(event => {
        if (n === 0) {
            return
        }
        const rect = event.currentTarget.getBoundingClientRect()
        if (rect.width <= 0) {
            return
        }
        const frac = (event.clientX - rect.left) / rect.width
        const idx = Math.min(n - 1, Math.max(0, Math.floor(frac * n)))
        setHoverIndex(idx)
    }, [
        n,
    ])

    const clearHover = useCallback(() => setHoverIndex(null), [])

    const handleMomentClick = useCallback(moment => {
        setSelectedTs(moment.t)
        if (onJump) {
            onJump(moment.t)
        }
    }, [
        onJump,
    ])

    // Re-derive the selected moment from the (possibly refetched) moments list so its
    // review status/enrichment reflects the latest data after a mutation invalidation.
    const activeMoment = useMemo(() => {
        if (selectedTs == null) {
            return null
        }
        return moments.find(m => m.t === selectedTs) || null
    }, [
        selectedTs,
        moments,
    ])

    const streamId = timeline?.streamId
    const handleReview = useCallback(status => {
        if (!streamId || selectedTs == null) {
            return
        }
        reviewMutation.mutate({
            streamId,
            bucketMinute: selectedTs,
            status,
        })
    }, [
        reviewMutation,
        streamId,
        selectedTs,
    ])

    // Graceful degradation: no buckets -> no chart card at all.
    if (n === 0) {
        return null
    }

    const barSlot = VW / n
    const barWidth = Math.max(1, barSlot * 0.72)
    const hovered = hoverIndex == null ? null : buckets[hoverIndex]

    // Nearest viewer sample to the hovered bucket, for the combined tooltip.
    let hoveredViewers = null
    if (hovered && viewerLane) {
        let bestD = Infinity
        for (const p of viewerLane.points) {
            const d = Math.abs(p.idxFrac - hoverIndex)
            if (d < bestD) {
                bestD = d
                hoveredViewers = p.viewers
            }
        }
    }

    const crosshairLeft = hovered
        ? `calc(2.6rem + ${((hoverIndex + 0.5) / n)} * (100% - 2.6rem))`
        : null

    const vodHref = activeMoment
        ? vodDeepLink(timeline?.twitchId, timeline?.streamStart, activeMoment.t)
        : null

    const topPhrases = activeMoment?.topPhrases || []
    const sampleMessages = activeMoment?.sampleMessages || []
    const reviewPending = reviewMutation.isPending

    return (
        <Card className="stream-timeline">
            <Card.Body>
                <div className="timeline-head">
                    <h3
                        id="timeline-heading"
                        className="section-label mb-0">
                        Chat activity
                    </h3>
                    <span className="timeline-subtitle">messages / minute</span>
                </div>

                <div className="timeline-lanes">
                    <div className="timeline-chart">
                        <span
                            className="timeline-axis-max"
                            aria-hidden="true">
                            {maxCount.toLocaleString()}
                        </span>
                        <span
                            className="timeline-axis-zero"
                            aria-hidden="true">
                            0
                        </span>

                        <svg
                            className="timeline-svg"
                            viewBox={`0 0 ${VW} ${VH}`}
                            preserveAspectRatio="none"
                            role="img"
                            aria-labelledby="timeline-heading"
                            onMouseMove={handleMove}
                            onMouseLeave={clearHover}>
                            {buckets.map((bucket, index) => {
                                const height = ((bucket.count || 0) / maxCount) * VH
                                const x = index * barSlot + (barSlot - barWidth) / 2
                                return (
                                    <rect
                                        key={bucket.t}
                                        className={`timeline-bar${
                                            index === hoverIndex ? ' timeline-bar--hover' : ''
                                        }`}
                                        x={x}
                                        y={VH - height}
                                        width={barWidth}
                                        height={Math.max(0, height)}
                                    />
                                )
                            })}
                        </svg>

                        <div className="timeline-markers">
                            {moments.map(moment => (
                                <button
                                    key={moment.t}
                                    type="button"
                                    className={`timeline-marker${
                                        selectedTs === moment.t ? ' timeline-marker--active' : ''
                                    }`}
                                    style={{ left: `${markerLeft(moment.t)}%` }}
                                    aria-label={`Spike at ${clock(moment.t)} — ${(
                                        moment.count || 0
                                    ).toLocaleString()} messages${
                                        moment.score ? ` (${moment.score}x baseline)` : ''
                                    }. Jump replay here.`}
                                    onClick={() => handleMomentClick(moment)}>
                                    <span
                                        className="timeline-marker-stem"
                                        aria-hidden="true" />
                                </button>
                            ))}
                        </div>
                    </div>

                    {viewerLane ? (
                        <div className="timeline-viewers">
                            <span
                                className="timeline-viewers-max"
                                aria-hidden="true">
                                {viewerLane.maxViewers.toLocaleString()} viewers
                            </span>
                            <svg
                                className="timeline-viewers-svg"
                                viewBox={`0 0 ${VW} ${VVH}`}
                                preserveAspectRatio="none"
                                role="img"
                                aria-label="Viewer count over time"
                                onMouseMove={handleMove}
                                onMouseLeave={clearHover}>
                                {viewerLane.area ? (
                                    <path
                                        className="timeline-viewers-area"
                                        d={viewerLane.area} />
                                ) : null}
                                <polyline
                                    className="timeline-viewers-line"
                                    points={viewerLane.line}
                                    vectorEffect="non-scaling-stroke" />
                            </svg>
                        </div>
                    ) : null}

                    {hovered ? (
                        <div
                            className="timeline-crosshair"
                            style={{ left: crosshairLeft }}
                            aria-hidden="true" />
                    ) : null}

                    {hovered ? (
                        <div
                            className="chart-tooltip"
                            style={{ left: crosshairLeft }}
                            role="status">
                            <span className="chart-tooltip-time">{clock(hovered.t)}</span>
                            <span className="chart-tooltip-metric">
                                {(hovered.count || 0).toLocaleString()} msgs
                            </span>
                            <span className="chart-tooltip-metric text-muted">
                                {(hovered.unique || 0).toLocaleString()} chatters
                            </span>
                            {hoveredViewers != null ? (
                                <span className="chart-tooltip-metric chart-tooltip-metric--viewers">
                                    {hoveredViewers.toLocaleString()} viewers
                                </span>
                            ) : null}
                            {hovered.subMessages != null ? (
                                <span className="chart-tooltip-metric text-muted">
                                    {hovered.subMessages.toLocaleString()} sub msgs
                                </span>
                            ) : null}
                            {hovered.emoteMessages != null ? (
                                <span className="chart-tooltip-metric text-muted">
                                    {hovered.emoteMessages.toLocaleString()} emote msgs
                                </span>
                            ) : null}
                        </div>
                    ) : null}
                </div>

                <div className="timeline-axis-x">
                    <span>{clock(buckets[0].t)}</span>
                    <span>{clock(buckets[n - 1].t)}</span>
                </div>

                {viewerLane ? (
                    <div className="stack-legend timeline-legend">
                        <span className="legend-chip legend-chip--messages">Messages</span>
                        <span className="legend-chip legend-chip--viewers">Viewers</span>
                    </div>
                ) : null}

                {activeMoment ? (
                    <div className="timeline-selection">
                        <div className="timeline-selection-head">
                            <span className="timeline-selection-label">
                                Jumped replay to {clock(activeMoment.t)}
                                {activeMoment.score ? ` · ${activeMoment.score}x baseline` : ''}
                            </span>
                            {activeMoment.status ? (
                                <span
                                    className={`status-chip ${
                                        activeMoment.status === 'bookmarked' ? 'is-ok' : 'is-err'
                                    }`}>
                                    {activeMoment.status}
                                </span>
                            ) : null}
                            {vodHref ? (
                                <a
                                    className="timeline-vod-link"
                                    href={vodHref}
                                    target="_blank"
                                    rel="noopener noreferrer">
                                    Open on Twitch
                                </a>
                            ) : null}
                        </div>

                        {(activeMoment.subShare != null || activeMoment.emoteShare != null) ? (
                            <div className="timeline-shares">
                                {activeMoment.subShare != null ? (
                                    <span className="timeline-share">
                                        <span className="timeline-share-label">Sub share</span>
                                        <span className="timeline-share-value">
                                            {pct(activeMoment.subShare)}
                                        </span>
                                    </span>
                                ) : null}
                                {activeMoment.emoteShare != null ? (
                                    <span className="timeline-share">
                                        <span className="timeline-share-label">Emote share</span>
                                        <span className="timeline-share-value">
                                            {pct(activeMoment.emoteShare)}
                                        </span>
                                    </span>
                                ) : null}
                            </div>
                        ) : null}

                        {topPhrases.length ? (
                            <div className="timeline-phrases">
                                {topPhrases.map(p => (
                                    <span
                                        key={p.phrase}
                                        className="timeline-phrase-chip">
                                        {p.phrase}
                                        <span className="timeline-phrase-count">
                                            {(p.count || 0).toLocaleString()}
                                        </span>
                                    </span>
                                ))}
                            </div>
                        ) : null}

                        {sampleMessages.length ? (
                            <ul className="timeline-samples">
                                {sampleMessages.map((s, i) => (
                                    <li
                                        key={`${i}-${s.text}`}
                                        className="timeline-sample">
                                        <span className="timeline-sample-text">{s.text}</span>
                                        {s.count > 1 ? (
                                            <span className="timeline-sample-count">
                                                ×{s.count.toLocaleString()}
                                            </span>
                                        ) : null}
                                    </li>
                                ))}
                            </ul>
                        ) : null}

                        {isAdmin ? (
                            <div className="timeline-review-actions">
                                <button
                                    type="button"
                                    className={`timeline-review-btn${
                                        activeMoment.status === 'bookmarked' ? ' is-active' : ''
                                    }`}
                                    disabled={reviewPending}
                                    onClick={() => handleReview('bookmarked')}>
                                    <i
                                        className="bi bi-bookmark-star"
                                        aria-hidden="true" /> Bookmark
                                </button>
                                <button
                                    type="button"
                                    className={`timeline-review-btn timeline-review-btn--reject${
                                        activeMoment.status === 'rejected' ? ' is-active' : ''
                                    }`}
                                    disabled={reviewPending}
                                    onClick={() => handleReview('rejected')}>
                                    <i
                                        className="bi bi-x-octagon"
                                        aria-hidden="true" /> Reject
                                </button>
                                {activeMoment.status ? (
                                    <button
                                        type="button"
                                        className="timeline-review-btn timeline-review-btn--clear"
                                        disabled={reviewPending}
                                        onClick={() => handleReview(null)}>
                                        Clear
                                    </button>
                                ) : null}
                            </div>
                        ) : null}
                    </div>
                ) : null}
            </Card.Body>
        </Card>
    )
}

export default StreamTimeline
