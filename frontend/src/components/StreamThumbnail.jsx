import React, {
    useCallback,
    useMemo,
} from 'react'
import {
    Card,
} from 'react-bootstrap'
import PropTypes from 'prop-types'
import { useNavigate } from 'react-router-dom'
import { findThumbnailSrc } from '../utils'
import { THUMBNAIL } from '../constants'
import {
    formatTimeAgo, formatDurationBetween,
} from '../utils/dateUtils'

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
    const navigate = useNavigate()
    // Memoize the navigation handler to prevent re-creation on every render
    const handleNavigation = useCallback(() => navigate(`/stream/${id}`), [
        navigate,
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

    return (
        <Card className="mx-2 hover-zoom">
            <div
                onClick={handleNavigation}
                onKeyDown={handleKeyDown}
                role="button"
                tabIndex="0"
                aria-label={`View details for ${name}'s stream with ${messageCount} messages`}
                style={{ cursor: 'pointer' }}
            >
                <Card.Img
                    src={thumbnailUrl}
                    variant="top"
                    width="100%"
                    alt={`Stream thumbnail for ${name}`}
                />
                <Card.Body>
                    <Card.Title as="h3">
                        {name}
                    </Card.Title>
                    <dl>
                        <dt className="visually-hidden">Message count:</dt>
                        <dd>Message count: <span className="fw-bold">{messageCount}</span></dd>

                        <dt className="visually-hidden">Time ago:</dt>
                        <dd>From now: <span className="fw-bold">{timeAgo}</span></dd>

                        <dt className="visually-hidden">Duration:</dt>
                        <dd>Duration: <span className="fw-bold">{duration}</span></dd>
                    </dl>
                </Card.Body>
            </div>
        </Card>
    )
}

StreamThumbnail.propTypes = {
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    start: PropTypes.string.isRequired,
    end: PropTypes.string.isRequired,
    thumbnailSrc: PropTypes.string.isRequired,
    messageCount: PropTypes.number.isRequired,
}

export default React.memo(StreamThumbnail)
