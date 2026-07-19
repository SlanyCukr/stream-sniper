'use client'
import {
    useCallback, useMemo, useState, type MouseEvent,
} from 'react'
import { Card } from 'react-bootstrap'
import { vodDeepLink } from '@/utils/vodChapters'
import { useAuth } from '@/contexts/AuthContext'
import { useMomentReview } from '@/hooks/moments/useMomentsQueries'
import { getHoverIndex, useTimelineGeometry } from '@/hooks/stream/timeline/useTimelineGeometry'
import type {
    StreamTimeline as StreamTimelineData,
    TimelineMoment,
} from '@/hooks/stream/timeline/useStreamTimelineQuery'
import type { MomentReviewStatus } from '@/lib/api/moments'
import CopyChaptersButton from '@/components/stream/timeline/CopyChaptersButton'
import TimelineLanes from '@/components/stream/timeline/TimelineLanes'
import TimelineContextList from '@/components/stream/timeline/TimelineContextList'
import TimelineSelection from '@/components/stream/timeline/TimelineSelection'

const EMPTY_LIST: never[] = []

// Only the fields this coordinator (and the regions it delegates to) actually
// reads — narrower than the full StreamTimeline query result so callers with
// a partial/mocked timeline aren't forced to supply bucketSeconds/metrics/
// peakViewers, which nothing here uses.
type StreamTimelineForCoordinator = Pick<
    StreamTimelineData,
    'streamId' | 'twitchVodId' | 'streamStart' | 'buckets' | 'moments' | 'viewerSamples' | 'contextChanges'
>

interface StreamTimelineProps {
    timeline: StreamTimelineForCoordinator | null | undefined
    onJump?: (t: string) => void
}

/**
 * Coordinates timeline selection and moment review while delegating chart
 * geometry and the three presentation regions to focused boundaries.
 */
const StreamTimeline = ({ timeline, onJump }: StreamTimelineProps) => {
    const { isAdmin } = useAuth()
    const reviewMutation = useMomentReview()
    const [hoverIndex, setHoverIndex] = useState<number | null>(null)
    const [selectedTs, setSelectedTs] = useState<string | null>(null)

    const buckets = timeline?.buckets || EMPTY_LIST
    const moments = timeline?.moments || EMPTY_LIST
    const viewerSamples = timeline?.viewerSamples || EMPTY_LIST
    const contextChanges = timeline?.contextChanges || EMPTY_LIST
    const geometry = useTimelineGeometry(buckets, viewerSamples, hoverIndex)

    const handleMove = useCallback((event: MouseEvent<SVGSVGElement>) => {
        const rect = event.currentTarget.getBoundingClientRect()
        setHoverIndex(getHoverIndex(
            event.clientX,
            rect.left,
            rect.width,
            geometry.bucketCount,
        ))
    }, [geometry.bucketCount])

    const handleMomentClick = useCallback((moment: TimelineMoment) => {
        setSelectedTs(moment.t)
        onJump?.(moment.t)
    }, [onJump])

    const activeMoment = useMemo(
        () => selectedTs == null
            ? null
            : moments.find(moment => moment.t === selectedTs) || null,
        [selectedTs, moments],
    )

    const handleReview = useCallback((nextStatus: MomentReviewStatus | null) => {
        const streamId = timeline?.streamId
        if (!streamId || selectedTs == null || !activeMoment?.isPersisted) return
        const target = { streamId, bucketMinute: selectedTs }
        reviewMutation.mutate(nextStatus === null
            ? { action: 'clear', ...target }
            : {
                action: 'set',
                ...target,
                status: nextStatus,
                clipUrl: null,
                note: null,
            })
    }, [reviewMutation, timeline?.streamId, selectedTs, activeMoment])

    if (geometry.bucketCount === 0) return null

    const vodHref = activeMoment
        ? vodDeepLink(timeline?.twitchVodId, timeline?.streamStart, activeMoment.t)
        : null

    return (
        <Card className="stream-timeline">
            <Card.Body>
                <div className="timeline-head">
                    <h3 id="timeline-heading" className="section-label mb-0">Chat activity</h3>
                    <span className="timeline-subtitle">messages / minute</span>
                    <CopyChaptersButton timeline={timeline} />
                </div>
                <TimelineLanes
                    buckets={buckets}
                    moments={moments}
                    contextChanges={contextChanges}
                    selectedTs={selectedTs}
                    hoverIndex={hoverIndex}
                    geometry={geometry}
                    onMove={handleMove}
                    onLeave={() => setHoverIndex(null)}
                    onMomentClick={handleMomentClick} />
                <TimelineContextList contextChanges={contextChanges} />
                <TimelineSelection
                    activeMoment={activeMoment}
                    vodHref={vodHref}
                    isAdmin={isAdmin}
                    reviewMutation={reviewMutation}
                    onReview={handleReview} />
            </Card.Body>
        </Card>
    )
}

export default StreamTimeline
