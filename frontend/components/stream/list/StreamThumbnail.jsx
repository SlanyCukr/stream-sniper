// @ts-check
'use client'
import React, {
    useCallback,
} from 'react'
import {
    Card,
} from 'react-bootstrap'
import { useRouter } from 'next/navigation'
import { expandThumbnailUrl } from './thumbnailUrl'
import ThumbImage from './ThumbImage'
import { THUMBNAIL } from '@/lib/stream/config'
import {
    formatTimeAgo, formatDurationBetween,
} from '@/utils/dateUtils'

/**
 * @param {{
 *   id: number,
 *   name: string,
 *   start: Date|string|number,
 *   end: Date|string|number|null,
 *   thumbnailSrc: string|null,
 *   messageCount: number,
 * }} props
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
    const handleNavigation = useCallback(() => router.push(`/stream/${id}`), [
        router,
        id,
    ])

    const handleKeyDown = useCallback(
    /** @param {React.KeyboardEvent<HTMLDivElement>} event */
    event => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            handleNavigation()
        }
    }, [
        handleNavigation,
    ])

    const thumbnailUrl = expandThumbnailUrl(thumbnailSrc, THUMBNAIL.WIDTH, THUMBNAIL.HEIGHT)
    const timeAgo = formatTimeAgo(start)
    const duration = formatDurationBetween(start, end)

    const isLive = !end

    return (
        <Card className="stream-card">
            <div
                onClick={handleNavigation}
                onKeyDown={handleKeyDown}
                role="button"
                tabIndex={0}
                aria-label={`View details for ${name}'s stream with ${messageCount} messages`}
            >
                <div className="thumb-wrap">
                    <ThumbImage
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
