'use client'
import {
    useState,
    useMemo,
    useCallback,
} from 'react'
import { Card } from 'react-bootstrap'
import { vodDeepLink } from '@/utils/chatRender'

// SVG geometry. preserveAspectRatio="none" stretches these units to the container
// box, so bars scale with width/height; text/markers live in the HTML overlay to
// avoid stroke/label distortion.
const VW = 1000
const VH = 160

/** Local naive "YYYY-MM-DDTHH:MM:SS" -> "HH:MM" without timezone drift. */
const clock = ts => (typeof ts === 'string' && ts.length >= 16 ? ts.slice(11, 16) : '')

/**
 * Stream chat-activity timeline: an inline-SVG messages-per-minute bar chart
 * (single phosphor series) overlaid with amber spike markers rendered as
 * focusable buttons. Clicking a marker jumps the replay to that moment and
 * reveals a Twitch VOD deep-link. Renders nothing when there are no buckets, so
 * the replay still works without rollups.
 * @param {object} props
 * @param {object} props.timeline - mapped timeline: {streamStart, twitchId, buckets, moments}
 * @param {function} props.onJump - (bucketMinuteIso) => void; jump the replay to a moment
 */
const StreamTimeline = ({ timeline, onJump }) => {
    const [
        hoverIndex,
        setHoverIndex,
    ] = useState(null)
    const [
        selectedMoment,
        setSelectedMoment,
    ] = useState(null)

    const buckets = useMemo(() => timeline?.buckets || [], [
        timeline?.buckets,
    ])
    const moments = useMemo(() => timeline?.moments || [], [
        timeline?.moments,
    ])

    const n = buckets.length

    const maxCount = useMemo(
        () => Math.max(1, ...buckets.map(b => b.count || 0)),
        [
            buckets,
        ],
    )

    // Marker x-position (percent of chart width) keyed to its bucket index; falls
    // back to the time fraction when a moment has no exact bucket match.
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

    const handleMomentClick = useCallback(moment => {
        setSelectedMoment(moment)
        if (onJump) {
            onJump(moment.t)
        }
    }, [
        onJump,
    ])

    // Graceful degradation: no buckets -> no chart card at all.
    if (n === 0) {
        return null
    }

    const barSlot = VW / n
    const barWidth = Math.max(1, barSlot * 0.72)
    const hovered = hoverIndex == null ? null : buckets[hoverIndex]

    const vodHref = selectedMoment
        ? vodDeepLink(timeline?.twitchId, timeline?.streamStart, selectedMoment.t)
        : null

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
                        aria-labelledby="timeline-heading">
                        {buckets.map((bucket, index) => {
                            const height = ((bucket.count || 0) / maxCount) * VH
                            const x = index * barSlot + (barSlot - barWidth) / 2
                            return (
                                <rect
                                    key={bucket.t}
                                    className="timeline-bar"
                                    x={x}
                                    y={VH - height}
                                    width={barWidth}
                                    height={Math.max(0, height)}
                                    onMouseEnter={() => setHoverIndex(index)}
                                    onMouseLeave={() => setHoverIndex(null)}
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
                                    selectedMoment?.t === moment.t ? ' timeline-marker--active' : ''
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

                    {hovered ? (
                        <div
                            className="chart-tooltip"
                            style={{ left: `${((hoverIndex + 0.5) / n) * 100}%` }}
                            role="status">
                            <span className="chart-tooltip-time">{clock(hovered.t)}</span>
                            <span className="chart-tooltip-metric">
                                {(hovered.count || 0).toLocaleString()} msgs
                            </span>
                            <span className="chart-tooltip-metric text-muted">
                                {(hovered.unique || 0).toLocaleString()} chatters
                            </span>
                        </div>
                    ) : null}
                </div>

                <div className="timeline-axis-x">
                    <span>{clock(buckets[0].t)}</span>
                    <span>{clock(buckets[n - 1].t)}</span>
                </div>

                {selectedMoment ? (
                    <div className="timeline-selection">
                        <span className="timeline-selection-label">
                            Jumped replay to {clock(selectedMoment.t)}
                            {selectedMoment.score ? ` · ${selectedMoment.score}x baseline` : ''}
                        </span>
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
                ) : null}
            </Card.Body>
        </Card>
    )
}

export default StreamTimeline
