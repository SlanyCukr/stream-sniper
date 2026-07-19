import { memo, type MouseEvent } from 'react'
import {
    MESSAGE_HEIGHT,
    TIMELINE_WIDTH,
    type useTimelineGeometry,
} from '@/hooks/stream/timeline/useTimelineGeometry'
import type {
    TimelineBucket,
    TimelineContextChange,
    TimelineMoment,
} from '@/hooks/stream/timeline/useStreamTimelineQuery'
import TimelineMarkers, { formatTimelineClock } from './TimelineMarkers'

type TimelineGeometry = ReturnType<typeof useTimelineGeometry>

interface TimelineBarsProps {
    buckets: TimelineBucket[]
    maxCount: number
    barSlot: number
    barWidth: number
}

const TimelineBars = memo(({
    buckets, maxCount, barSlot, barWidth,
}: TimelineBarsProps) => buckets.map((bucket, index) => {
    const height = ((bucket.count || 0) / maxCount) * MESSAGE_HEIGHT
    return (
        <rect
            key={bucket.t}
            className="timeline-bar"
            x={index * barSlot + (barSlot - barWidth) / 2}
            y={MESSAGE_HEIGHT - height}
            width={barWidth}
            height={Math.max(0, height)} />
    )
}))
TimelineBars.displayName = 'TimelineBars'

interface TimelineHoverTooltipProps {
    hovered: TimelineBucket | null
    hoveredViewers: number | null
    crosshairLeft: string | null
}

const TimelineHoverTooltip = ({ hovered, hoveredViewers, crosshairLeft }: TimelineHoverTooltipProps) => {
    if (!hovered) return null
    return (
        <div className="chart-tooltip" style={{ left: crosshairLeft ?? undefined }} role="status">
            <span className="chart-tooltip-time">{formatTimelineClock(hovered.t)}</span>
            <span className="chart-tooltip-metric">{(hovered.count || 0).toLocaleString()} msgs</span>
            <span className="chart-tooltip-metric text-muted">{(hovered.unique || 0).toLocaleString()} chatters</span>
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
    )
}

interface TimelineMessageChartProps {
    buckets: TimelineBucket[]
    moments: TimelineMoment[]
    contextChanges: TimelineContextChange[]
    selectedTs: string | null
    hoverIndex: number | null
    geometry: TimelineGeometry
    onMove: (event: MouseEvent<SVGSVGElement>) => void
    onLeave: () => void
    onMomentClick: (moment: TimelineMoment) => void
}

const TimelineMessageChart = ({
    buckets,
    moments,
    contextChanges,
    selectedTs,
    hoverIndex,
    geometry,
    onMove,
    onLeave,
    onMomentClick,
}: TimelineMessageChartProps) => {
    const {
        maxCount,
        markerLeft,
        hovered,
        hoveredHeight,
        hoveredViewers,
        barSlot,
        barWidth,
        crosshairLeft,
    } = geometry
    return (
        <div className="timeline-chart">
            <span className="timeline-axis-max" aria-hidden="true">{maxCount.toLocaleString()}</span>
            <span className="timeline-axis-zero" aria-hidden="true">0</span>
            <svg
                className="timeline-svg"
                viewBox={`0 0 ${TIMELINE_WIDTH} ${MESSAGE_HEIGHT}`}
                preserveAspectRatio="none"
                role="img"
                aria-labelledby="timeline-heading"
                onMouseMove={onMove}
                onMouseLeave={onLeave}>
                <TimelineBars {...{ buckets, maxCount, barSlot, barWidth }} />
                {hovered ? (
                    <rect
                        className="timeline-bar timeline-bar--hover"
                        // `hovered` truthy implies hoverIndex is not null, but TS can't link the two props.
                        x={(hoverIndex as number) * barSlot + (barSlot - barWidth) / 2}
                        y={MESSAGE_HEIGHT - hoveredHeight}
                        width={barWidth}
                        height={Math.max(0, hoveredHeight)} />
                ) : null}
            </svg>
            <TimelineMarkers {...{
                contextChanges,
                moments,
                selectedTs,
                markerLeft,
                onMomentClick,
            }} />
            <TimelineHoverTooltip {...{ hovered, hoveredViewers, crosshairLeft }} />
        </div>
    )
}

export default TimelineMessageChart
