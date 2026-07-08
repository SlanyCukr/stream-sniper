'use client'
import React, { useState } from 'react'

/**
 * Stream thumbnail image with a night-ops "no feed" fallback when the
 * source 404s (Twitch VOD thumbnails are often missing/still processing).
 */
const ThumbImage = ({
    src, alt,
}) => {
    const [
        failed,
        setFailed,
    ] = useState(false)

    if (failed || !src) {
        return (
            <div
                className="thumb-fallback"
                role="img"
                aria-label={alt}
            >
                <i
                    className="bi bi-camera-video-off"
                    aria-hidden="true"></i>
                <span>No feed</span>
            </div>
        )
    }

    return (
        <img
            src={src}
            alt={alt}
            onError={() => setFailed(true)}
        />
    )
}

export default React.memo(ThumbImage)
