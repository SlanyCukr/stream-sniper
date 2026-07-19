/**
 * Twitch VOD deep-link + chapter-list helpers. Kept separate from
 * chatRender.jsx so checkJs boundary files can import them without pulling the
 * (unchecked) chat-render module into the typecheck graph.
 */

/**
 * Build a twitch.tv VOD deep link that seeks to a moment's offset.
 *
 * @param twitchVodId - The VOD id
 * @param streamStart - ISO timestamp of the stream start
 * @param momentTs - ISO timestamp of the moment to seek to
 * @returns A twitch.tv/videos deep-link, or null when there is no VOD id
 */
export const vodDeepLink = (
    twitchVodId: string | number | null,
    streamStart: string,
    momentTs: string,
): string | null => {
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

interface VodChaptersTimeline {
    twitchVodId: string | number | null
    streamStart: string
    moments: Array<{ t: string, count: number, topPhrases?: string[] | null }>
}

/**
 * Build a shareable chapter list for a stream's detected moments: one line per
 * moment with its VOD offset, a label (top chat phrase when available), the
 * message count, and a Twitch deep link.
 *
 * @returns Chapter text, or null when there is no VOD or no moments
 */
export const buildVodChapters = (timeline: VodChaptersTimeline | null | undefined): string | null => {
    if (!timeline?.twitchVodId || !timeline.moments?.length) {
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
        const label = moment.topPhrases?.[0] || 'chat spike'
        const link = vodDeepLink(timeline.twitchVodId, timeline.streamStart, moment.t)
        return `${stamp} — ${label} (${moment.count} msgs) ${link}`
    })
    return lines.join('\n')
}
