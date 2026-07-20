import { memo } from 'react'
import type { TimelineContextChange, TimelineMoment } from '@/hooks/stream/timeline/useStreamTimelineQuery'

export const formatTimelineClock = (timestamp: unknown): string => typeof timestamp === 'string' && timestamp.length >= 16
    ? timestamp.slice(11, 16)
    : ''

interface TimelineMarkersProps {
    contextChanges: TimelineContextChange[]
    moments: TimelineMoment[]
    selectedTs: string | null
    markerLeft: (timestamp: string) => number
    onMomentClick: (moment: TimelineMoment) => void
}

// Memoized like its hover-sensitive siblings (TimelineBars, TimelineViewerPaths):
// markers don't depend on hover state, so hover-driven parent renders skip them.
const TimelineMarkers = memo(({
    contextChanges,
    moments,
    selectedTs,
    markerLeft,
    onMomentClick,
}: TimelineMarkersProps) => (
    <div className="timeline-markers">
        {contextChanges.map(change => (
            <span
                key={`context-${change.t}`}
                className="timeline-context-marker"
                style={{ left: `${markerLeft(change.t)}%` }}
                title={`${formatTimelineClock(change.t)} · ${change.categoryName || 'Uncategorized'} · ${change.title || 'Untitled'}`}
                aria-label={`Context changed at ${formatTimelineClock(change.t)} to ${change.categoryName || 'uncategorized'}: ${change.title || 'untitled'}`}
                role="img" />
        ))}
        {moments.map(moment => (
            <button
                key={moment.t}
                type="button"
                className={`timeline-marker${selectedTs === moment.t ? ' timeline-marker--active' : ''}`}
                style={{ left: `${markerLeft(moment.t)}%` }}
                aria-label={`Spike at ${formatTimelineClock(moment.t)} — ${(moment.count || 0).toLocaleString()} messages${moment.score ? ` (${moment.score}x baseline)` : ''}. Jump replay here.`}
                onClick={() => onMomentClick(moment)}>
                <span className="timeline-marker-stem" aria-hidden="true" />
            </button>
        ))}
    </div>
))

TimelineMarkers.displayName = 'TimelineMarkers'

export default TimelineMarkers
