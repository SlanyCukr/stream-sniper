import React from 'react'
import Image from 'next/image'
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
 * Presentation metadata per Twitch badge name: a bootstrap-icon class + a modifier
 * class carrying its accent color + a human-readable label for the sr-only alt text.
 * Names not in this map fall back to a small neutral dot (DEFAULT_BADGE, icon: null).
 */
const BADGE_META = {
    broadcaster: {
        icon: 'bi-camera-video-fill',
        className: 'chat-badge--broadcaster',
        label: 'Broadcaster',
    },
    moderator: {
        icon: 'bi-shield-fill',
        className: 'chat-badge--moderator',
        label: 'Moderator',
    },
    vip: {
        icon: 'bi-gem',
        className: 'chat-badge--vip',
        label: 'VIP',
    },
    subscriber: {
        icon: 'bi-star-fill',
        className: 'chat-badge--subscriber',
        label: 'Subscriber',
    },
    founder: {
        icon: 'bi-star-fill',
        className: 'chat-badge--subscriber',
        label: 'Founder',
    },
}

const DEFAULT_BADGE = {
    icon: null,
    className: 'chat-badge--other',
    label: null,
}

/**
 * Parses a raw Twitch badges string ("moderator/1,subscriber/12") into structured,
 * render-ready entries. Returns [] for null/empty (legacy rows collected before
 * badge capture) so callers render nothing rather than a placeholder.
 * @param {string|null|undefined} badges
 * @returns {Array<{name: string, version: string, raw: string, icon: string|null, className: string, label: string}>}
 */
export const parseBadges = badges => {
    if (!badges) {
        return []
    }

    return String(badges)
        .split(',')
        .map(part => part.trim())
        .filter(Boolean)
        .map(part => {
            const slash = part.indexOf('/')
            const name = slash >= 0 ? part.slice(0, slash) : part
            const version = slash >= 0 ? part.slice(slash + 1) : ''
            const meta = BADGE_META[name] || DEFAULT_BADGE
            return {
                name,
                version,
                raw: part,
                icon: meta.icon,
                className: meta.className,
                label: meta.label || name,
            }
        })
        .filter(badge => badge.name)
}

/** @param {string} message @returns {JSX.Element[]|null} */
export const renderMessageWithBetterTtvEmotes = message => {
    if (!message) {
        return null
    }

    return message
        .split(' ')
        .map((word, index) => {
            if (word in EMOTES) {
                return (
                    <Image
                        key={index}
                        src={`https://cdn.betterttv.net/emote/${EMOTES[word]}/1x`}
                        alt={word}
                        width={28}
                        height={28}
                        unoptimized
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
 * @param {string|number|null} twitchVodId - The VOD id
 * @param {string} streamStart - ISO timestamp of the stream start
 * @param {string} momentTs - ISO timestamp of the moment to seek to
 * @returns {string|null} A twitch.tv/videos deep-link, or null when there is no VOD id
 */
export const vodDeepLink = (twitchVodId, streamStart, momentTs) => {
    if (!twitchVodId) {
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
    return `https://www.twitch.tv/videos/${twitchVodId}?t=${h}h${m}m${s}s`
}
