'use client'
import React, {
    useCallback,
    useMemo,
} from 'react'
import {
    Card,
} from 'react-bootstrap'
import { useRouter } from 'next/navigation'
import { findThumbnailSrc } from '@/utils/utils'
import { THUMBNAIL } from '@/constants'
import {
    formatTimeAgo, formatDurationBetween,
} from '@/utils/dateUtils'

/**
 * Displays basic information about stream on AllStream component.
 * @param {Number} id           // id of the stream
 * @param {String} name         // name of the streamer
 * @param {String} start        // datetime when the stream started
 * @param {String} end          // datetime when the stream ended
 * @param {String} thumbnailSrc // thumbnail of the stream
 * @param {Number} messageCount // number of messages in this stream
 * @returns
 */
const StreamThumbnail = ({
    id,
    name,
    start,
    end,
    thumbnailSrc,
    messageCount,
}) => {
    const router = useRouter()
    // Memoize the navigation handler to prevent re-creation on every render
    const handleNavigation = useCallback(() => router.push(`/stream/${id}`), [
        router,
        id,
    ])

    // Handle keyboard navigation
    const handleKeyDown = useCallback(event => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            handleNavigation()
        }
    }, [
        handleNavigation,
    ])

    // Memoize thumbnail source calculation
    const thumbnailUrl = useMemo(() => findThumbnailSrc(thumbnailSrc, THUMBNAIL.WIDTH, THUMBNAIL.HEIGHT), [
        thumbnailSrc,
    ])

    // Memoize date calculations for performance
    const timeAgo = useMemo(() => formatTimeAgo(start), [
        start,
    ])
    const duration = useMemo(() => formatDurationBetween(start, end), [
        start,
        end,
    ])

    const isLive = !end

    return (
        <Card className="mx-2 stream-card">
            <div
                onClick={handleNavigation}
                onKeyDown={handleKeyDown}
                role="button"
                tabIndex="0"
                aria-label={`View details for ${name}'s stream with ${messageCount} messages`}
            >
                <div className="thumb-wrap">
                    <img
                        src={thumbnailUrl}
                        alt={`Stream thumbnail for ${name}`}
                    />
                    {isLive
                        ? <span className="live-chip">LIVE</span>
                        : <span className="duration-chip">{duration}</span>}
                </div>
                <Card.Body className="py-3">
                    <Card.Title
                        as="h3"
                        className="fs-5 mb-2 text-truncate">
                        {name}
                    </Card.Title>
                    <div className="stream-meta mb-1">
                        <span>MSGS</span>
                        <span className="value">{messageCount.toLocaleString()}</span>
                    </div>
                    <div className="stream-meta">
                        <span>AIRED</span>
                        <span className="value">{timeAgo}</span>
                    </div>
                </Card.Body>
            </div>
        </Card>
    )
}

export default React.memo(StreamThumbnail)
