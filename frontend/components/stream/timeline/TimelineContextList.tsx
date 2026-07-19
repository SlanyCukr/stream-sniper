import { formatTimelineClock } from './TimelineMarkers'
import type { TimelineContextChange } from '@/hooks/stream/timeline/useStreamTimelineQuery'

interface TimelineContextListProps {
    contextChanges: TimelineContextChange[]
}

const TimelineContextList = ({ contextChanges }: TimelineContextListProps) => contextChanges.length ? (
    <div className="timeline-context-list" aria-label="Stream context changes">
        {contextChanges.map(change => (
            <div key={change.t} className="timeline-context-item">
                <time>{formatTimelineClock(change.t)}</time>
                <span className="timeline-context-category">{change.categoryName || 'Uncategorized'}</span>
                <span className="timeline-context-title">{change.title || 'Untitled stream'}</span>
                {(change.tags || []).length ? <span className="timeline-context-tags">{change.tags.slice(0, 3).join(' · ')}</span> : null}
            </div>
        ))}
    </div>
) : null

export default TimelineContextList
