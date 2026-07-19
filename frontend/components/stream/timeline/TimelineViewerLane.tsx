import { memo, type MouseEvent } from 'react'
import {
    TIMELINE_WIDTH,
    VIEWER_HEIGHT,
    type ViewerLane,
} from '@/hooks/stream/timeline/useTimelineGeometry'

interface TimelineViewerPathsProps {
    area: string
    line: string
}

const TimelineViewerPaths = memo(({ area, line }: TimelineViewerPathsProps) => (
    <>
        {area ? <path className="timeline-viewers-area" d={area} /> : null}
        <polyline className="timeline-viewers-line" points={line} vectorEffect="non-scaling-stroke" />
    </>
))
TimelineViewerPaths.displayName = 'TimelineViewerPaths'

interface TimelineViewerLaneProps {
    viewerLane: ViewerLane | null
    onMove: (event: MouseEvent<SVGSVGElement>) => void
    onLeave: () => void
}

const TimelineViewerLane = ({ viewerLane, onMove, onLeave }: TimelineViewerLaneProps) => {
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
