'use client'
import React, { useState } from 'react'
import Image from 'next/image'

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
        <Image
            src={src}
            alt={alt}
            width={300}
            height={170}
            onError={() => setFailed(true)}
        />
    )
}

export default React.memo(ThumbImage)
