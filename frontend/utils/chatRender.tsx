import { type JSX } from 'react'
import Image from 'next/image'
import { EMOTES } from '@/lib/bettertv_emotes'

/* Twitch-style username palette (dark-theme readable). */
const NICK_COLORS = [
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
export const nickColor = (nick: string): string => {
    let hash = 0
    for (let i = 0; i < nick.length; i++) {
        hash = (hash * 31 + nick.charCodeAt(i)) | 0
    }
    return NICK_COLORS[Math.abs(hash) % NICK_COLORS.length]
}

interface BadgeMeta {
    icon: string | null
    className: string
    label: string | null
}

/**
 * Presentation metadata per Twitch badge name: a bootstrap-icon class + a modifier
 * class carrying its accent color + a human-readable label for the sr-only alt text.
 * Names not in this map fall back to a small neutral dot (DEFAULT_BADGE, icon: null).
 */
const BADGE_META: Record<string, BadgeMeta> = {
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

const DEFAULT_BADGE: BadgeMeta = {
    icon: null,
    className: 'chat-badge--other',
    label: null,
}

export interface ParsedBadge {
    name: string
    version: string
    raw: string
    icon: string | null
    className: string
    label: string
}

/**
 * Parses raw Twitch badges into structured, render-ready entries. The wire
 * sends an array of badge tokens ("moderator/1"); legacy call sites pass the
 * comma-joined string form — both stringify to the same "a/1,b/2" shape.
 * Returns [] for null/empty (legacy rows collected before badge capture) so
 * callers render nothing rather than a placeholder.
 */
export const parseBadges = (badges: unknown[] | string | null | undefined): ParsedBadge[] => {
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

export const renderMessageWithBetterTtvEmotes = (message: string): JSX.Element[] | null => {
    if (!message) {
        return null
    }

    return message
        .split(' ')
        .map((word, index) => {
            if (word in EMOTES) {
                // Runtime-checked via `in` above; the emote map's key type is a
                // fixed string-literal union inferred from JSON, not `string`.
                const emoteId = (EMOTES as Record<string, string>)[word]
                return (
                    <Image
                        key={index}
                        src={`https://cdn.betterttv.net/emote/${emoteId}/1x`}
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
