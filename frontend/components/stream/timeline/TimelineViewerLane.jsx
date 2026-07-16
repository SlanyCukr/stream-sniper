import { memo } from 'react'
import {
    TIMELINE_WIDTH,
    VIEWER_HEIGHT,
} from '@/hooks/stream/timeline/useTimelineGeometry'

const TimelineViewerPaths = memo(({ area, line }) => (
    <>
        {area ? <path className="timeline-viewers-area" d={area} /> : null}
        <polyline className="timeline-viewers-line" points={line} vectorEffect="non-scaling-stroke" />
    </>
))
TimelineViewerPaths.displayName = 'TimelineViewerPaths'

const TimelineViewerLane = ({ viewerLane, onMove, onLeave }) => {
    if (!viewerLane) return null
    return (
        <div className="timeline-viewers">
            <span className="timeline-viewers-max" aria-hidden="true">
                {viewerLane.maxViewers.toLocaleString()} viewers
            </span>
            <svg
                className="timeline-viewers-svg"
                viewBox={`0 0 ${TIMELINE_WIDTH} ${VIEWER_HEIGHT}`}
                preserveAspectRatio="none"
                role="img"
                aria-label="Viewer count over time"
                onMouseMove={onMove}
                onMouseLeave={onLeave}>
                <TimelineViewerPaths area={viewerLane.area} line={viewerLane.line} />
            </svg>
        </div>
    )
}

export default TimelineViewerLane
