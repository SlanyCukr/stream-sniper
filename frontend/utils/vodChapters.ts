/**
 * Twitch VOD deep-link + chapter-list helpers, typed to the timeline wire
 * contract (nullable stream start, validated phrase payloads) so callers
 * never need casts.
 */

/**
 * Build a twitch.tv VOD deep link that seeks to a moment's offset.
 *
 * @param twitchVodId - The VOD id
 * @param streamStart - ISO timestamp of the stream start (nullable on the wire)
 * @param momentTs - ISO timestamp of the moment to seek to
 * @returns A twitch.tv/videos deep-link, or null when there is no VOD id or no
 *   usable start time (an offset computed against a missing start would seek
 *   to a nonsense position).
 */
const offsetSeconds = (streamStart: string, momentTs: string): number => {
    const startMs = new Date(streamStart).getTime()
    const momentMs = new Date(momentTs).getTime()
    const offset = Math.floor((momentMs - startMs) / 1000)
    return Number.isFinite(offset) ? Math.max(0, offset) : 0
}

const twitchOffset = (offset: number): string => {
    const h = Math.floor(offset / 3600)
    const m = Math.floor((offset % 3600) / 60)
    const s = offset % 60
    return `${h}h${m}m${s}s`
}

const chapterOffset = (offset: number): string => {
    const h = Math.floor(offset / 3600)
    const m = Math.floor((offset % 3600) / 60)
    const s = offset % 60
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

const vodUrl = (twitchVodId: string | number, offset: number): string => (
    `https://www.twitch.tv/videos/${twitchVodId}?t=${twitchOffset(offset)}`
)

export const vodDeepLink = (
    twitchVodId: string | number | null | undefined,
    streamStart: string | null | undefined,
    momentTs: string,
): string | null => {
    if (!twitchVodId || !streamStart) {
        return null
    }
    return vodUrl(twitchVodId, offsetSeconds(streamStart, momentTs))
}

import type { MomentPhrase } from '@/lib/api/moments'

interface VodChaptersTimeline {
    twitchVodId: string | number | null
    streamStart: string | null
    moments: Array<{ t: string, count: number, topPhrases?: MomentPhrase[] | null }>
}

const momentLabel = (topPhrases: MomentPhrase[] | null | undefined): string => {
    const first = topPhrases?.[0]
    return first?.phrase || 'chat spike'
}

/**
 * Build a shareable chapter list for a stream's detected moments: one line per
 * moment with its VOD offset, a label (top chat phrase when available), the
 * message count, and a Twitch deep link.
 *
 * @returns Chapter text, or null when there is no VOD, no start time, or no moments
 */
export const buildVodChapters = (timeline: VodChaptersTimeline | null | undefined): string | null => {
    if (!timeline?.twitchVodId || !timeline.streamStart || !timeline.moments?.length) {
        return null
    }
    const { streamStart, twitchVodId } = timeline
    const lines = timeline.moments.map(moment => {
        const offset = offsetSeconds(streamStart, moment.t)
        const stamp = chapterOffset(offset)
        const label = momentLabel(moment.topPhrases)
        const link = vodUrl(twitchVodId, offset)
        return `${stamp} — ${label} (${moment.count} msgs) ${link}`
    })
    return lines.join('\n')
}
