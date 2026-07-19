'use client'
import React from 'react'
import { Card } from 'react-bootstrap'

interface StreamGridSkeletonProps {
    count?: number
}

/** Shimmering placeholder grid shown while streams load. */
const StreamGridSkeleton = ({ count = 8 }: StreamGridSkeletonProps) => (
    <div
        className="stream-grid"
        role="status"
        aria-label="Loading streams"
    >
        {Array.from({ length: count }, (_, index) => (
            <Card
                key={index}
                className="stream-card"
                aria-hidden="true"
            >
                <div className="skeleton skeleton-thumb" />
                <Card.Body className="py-3">
                    <div className="skeleton skeleton-line w-75" />
                    <div className="skeleton skeleton-line" />
                    <div className="skeleton skeleton-line w-50 mb-0" />
                </Card.Body>
            </Card>
        ))}
        <span className="visually-hidden">Loading streams…</span>
    </div>
)

export default React.memo(StreamGridSkeleton)
