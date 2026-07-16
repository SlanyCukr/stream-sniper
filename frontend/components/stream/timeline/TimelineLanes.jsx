import TimelineMessageChart from './TimelineMessageChart'
import TimelineViewerLane from './TimelineViewerLane'
import { formatTimelineClock } from './TimelineMarkers'

const TimelineLanes = ({
    buckets,
    moments,
    contextChanges,
    selectedTs,
    hoverIndex,
    geometry,
    onMove,
    onLeave,
    onMomentClick,
}) => {
    const {
        bucketCount,
        viewerLane,
        hovered,
        crosshairLeft,
    } = geometry
    return (
        <>
            <div className="timeline-lanes">
                <TimelineMessageChart {...{
                    buckets,
                    moments,
                    contextChanges,
                    selectedTs,
                    hoverIndex,
                    geometry,
                    onMove,
                    onLeave,
                    onMomentClick,
                }} />
                <TimelineViewerLane {...{ viewerLane, onMove, onLeave }} />
                {hovered ? <div className="timeline-crosshair" style={{ left: crosshairLeft }} aria-hidden="true" /> : null}
            </div>
            <div className="timeline-axis-x">
                <span>{formatTimelineClock(buckets[0].t)}</span>
                <span>{formatTimelineClock(buckets[bucketCount - 1].t)}</span>
            </div>
            {viewerLane ? (
                <div className="stack-legend timeline-legend">
                    <span className="legend-chip legend-chip--messages">Messages</span>
                    <span className="legend-chip legend-chip--viewers">Viewers</span>
                </div>
            ) : null}
        </>
    )
}

export default TimelineLanes
