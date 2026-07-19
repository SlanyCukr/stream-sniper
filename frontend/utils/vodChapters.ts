/**
 * Twitch VOD deep-link + chapter-list helpers, typed to the timeline wire
 * contract (nullable stream start, unknown-typed phrase payloads) so callers
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
export const vodDeepLink = (
    twitchVodId: string | number | null | undefined,
    streamStart: string | null | undefined,
    momentTs: string,
): string | null => {
    if (!twitchVodId || !streamStart) {
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

interface VodChaptersTimeline {
    twitchVodId: string | number | null
    streamStart: string | null
    moments: Array<{ t: string, count: number, topPhrases?: unknown[] | null }>
}

/** First phrase of a moment when it is a non-empty string; the wire types phrases as unknown[]. */
const momentLabel = (topPhrases: unknown[] | null | undefined): string => {
    const first = topPhrases?.[0]
    return typeof first === 'string' && first ? first : 'chat spike'
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
    const startMs = new Date(timeline.streamStart).getTime()
    const lines = timeline.moments.map(moment => {
        let offset = Math.max(0, Math.floor((new Date(moment.t).getTime() - startMs) / 1000))
        if (!Number.isFinite(offset)) {
            offset = 0
        }
        const h = Math.floor(offset / 3600)
        const m = Math.floor((offset % 3600) / 60)
        const s = offset % 60
        const stamp = `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
        const label = momentLabel(moment.topPhrases)
        const link = vodDeepLink(timeline.twitchVodId, timeline.streamStart, moment.t)
        return `${stamp} — ${label} (${moment.count} msgs) ${link}`
    })
    return lines.join('\n')
}
