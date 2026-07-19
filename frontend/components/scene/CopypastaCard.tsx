'use client'
import { useState } from 'react'
import Link from 'next/link'
import type { ScenePasta } from '@/hooks/scene/useSceneCopypastaQueries'

/** Naive UTC "YYYY-MM-DDTHH:MM:SS" -> "YYYY-MM-DD" date slice (no TZ drift). */
const dateOnly = (ts: string | null): string | null => (typeof ts === 'string' && ts.length >= 10 ? ts.slice(0, 10) : null)

// Texts longer than this are clamped with an expand toggle.
const CLAMP_CHARS = 240

interface CopypastaCardProps {
    /** mapped copypasta item from useSceneCopypastas */
    pasta: ScenePasta
}

/**
 * One copypasta row: the verbatim message text in a monospace block plus spread
 * chips (usage, channels, streams, first seen). Long pastas clamp to a preview
 * with an expand-on-click toggle. Nullable dates are omitted, never faked.
 */
const CopypastaCard = ({ pasta }: CopypastaCardProps) => {
    const {
        messageTextId,
        text,
        usageCount,
        streamCount,
        creatorCount,
        firstSeen,
    } = pasta

    const [
        expanded,
        setExpanded,
    ] = useState(false)

    const isLong = typeof text === 'string' && text.length > CLAMP_CHARS
    const firstSeenDate = dateOnly(firstSeen)

    return (
        <article className="pasta-card">
            <div className={`pasta-text mono${isLong && !expanded ? ' is-clamped' : ''}`}>
                {text}
            </div>

            {isLong ? (
                <button
                    type="button"
                    className="pasta-expand"
                    aria-expanded={expanded}
                    onClick={() => setExpanded(prev => !prev)}>
                    {expanded ? 'Show less' : 'Show more'}
                </button>
            ) : null}

            <div className="pasta-chips">
                <span className="pasta-chip mono">
                    {(usageCount ?? 0).toLocaleString()}
                    <span className="pasta-chip-unit"> uses</span>
                </span>
                <span className="pasta-chip mono">
                    {(creatorCount ?? 0).toLocaleString()}
                    <span className="pasta-chip-unit"> channels</span>
                </span>
                <span className="pasta-chip mono">
                    {(streamCount ?? 0).toLocaleString()}
                    <span className="pasta-chip-unit"> streams</span>
                </span>
                {firstSeenDate ? (
                    <span className="pasta-chip pasta-chip-muted mono">
                        first seen {firstSeenDate}
                    </span>
                ) : null}
                <Link className="pasta-chip pasta-trace-link" href={`/copypasta/${messageTextId}`}>
                    Trace spread →
                </Link>
            </div>
        </article>
    )
}

export default CopypastaCard
