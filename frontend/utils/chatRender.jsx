import React from 'react'
import { EMOTES } from '@/lib/bettertv_emotes'

/* Twitch-style username palette (dark-theme readable). */
export const NICK_COLORS = [
    '#ff7a7a',
    '#f5b759',
    '#9fef00',
    '#2dd4a7',
    '#58a6ff',
    '#c58fff',
    '#ff8fd0',
    '#5edfff',
    '#ffb86b',
    '#a3e635',
]

/** Deterministic color per nick so it stays stable across renders. */
export const nickColor = nick => {
    let hash = 0
    for (let i = 0; i < nick.length; i++) {
        hash = (hash * 31 + nick.charCodeAt(i)) | 0
    }
    return NICK_COLORS[Math.abs(hash) % NICK_COLORS.length]
}

/**
 * Applies BetterTV emotes to a message, replacing known emote words with <img> tags.
 * @param {string} message
 * @returns {JSX.Element[]|null}
 */
export const applyBetterTvEmotes = message => {
    if (!message) {
        return null
    }

    return message
        .split(' ')
        .map((word, index) => {
            if (word in EMOTES) {
                return (
                    <img
                        key={index}
                        src={`https://cdn.betterttv.net/emote/${EMOTES[word]}/1x`}
                        alt={word}
                        role="img"
                        aria-label={`${word} emote`}
                    />
                )
            }

            return <span key={index}>{word + ' '}</span>
        })
}

/**
 * Builds a Twitch VOD deep-link seeked to a moment's offset from the stream start.
 * @param {string|number|null} twitchId - The VOD id
 * @param {string} streamStart - ISO timestamp of the stream start
 * @param {string} momentTs - ISO timestamp of the moment to seek to
 * @returns {string|null} A twitch.tv/videos deep-link, or null when there is no VOD id
 */
export const vodDeepLink = (twitchId, streamStart, momentTs) => {
    if (!twitchId) {
        return null
    }
    const startMs = new Date(streamStart).getTime()
    const momentMs = new Date(momentTs).getTime()
    let offset = Math.max(0, Math.floor((momentMs - startMs) / 1000))
    if (!Number.isFinite(offset)) {
        offset = 0
    }
    const h = Math.floor(offset / 3600)
    const m = Math.floor((offset % 3600) / 60)
    const s = offset % 60
    return `https://www.twitch.tv/videos/${twitchId}?t=${h}h${m}m${s}s`
}
