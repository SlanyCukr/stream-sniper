'use client'
import React from 'react'

/** One row in a ranked chatter leaderboard. */
const ChatterSmallInfo = ({
    rank,
    nick,
    count,
    noun,
}) => (
    <li
        tabIndex="0"
        role="listitem"
        aria-label={`Rank ${rank}: ${nick}, ${count} ${noun}`}
    >
        <span
            className="rank"
            aria-hidden="true">
            {String(rank).padStart(2, '0')}
        </span>
        <span className="nick">{nick}</span>
        <span
            className="count"
            aria-hidden="true">
            {count?.toLocaleString()}
        </span>
    </li>
)

export default React.memo(ChatterSmallInfo)
