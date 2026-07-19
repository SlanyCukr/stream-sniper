import {
    describe, expect, it,
} from 'vitest'
import { buildVodChapters } from '@/utils/vodChapters'

const timeline = {
    twitchVodId: 123456,
    streamStart: '2026-07-16T17:00:00',
    moments: [
        {
            t: '2026-07-16T17:12:00',
            count: 312,
            topPhrases: [
                'LETS GO',
                'W',
            ],
        },
        {
            t: '2026-07-16T19:05:30',
            count: 88,
            topPhrases: null,
        },
    ],
}

describe('buildVodChapters', () => {
    it('builds one line per moment with offset, label, count, and deep link', () => {
        const chapters = buildVodChapters(timeline)

        expect(chapters).toBe([
            '0:12:00 — LETS GO (312 msgs) https://www.twitch.tv/videos/123456?t=0h12m0s',
            '2:05:30 — chat spike (88 msgs) https://www.twitch.tv/videos/123456?t=2h5m30s',
        ].join('\n'))
    })

    it('returns null without a VOD id', () => {
        expect(buildVodChapters({
            ...timeline,
            twitchVodId: null,
        })).toBeNull()
    })

    it('returns null without moments', () => {
        expect(buildVodChapters({
            ...timeline,
            moments: [],
        })).toBeNull()
        expect(buildVodChapters(null)).toBeNull()
    })

    it('clamps pre-start moments to offset zero', () => {
        const chapters = buildVodChapters({
            ...timeline,
            moments: [
                {
                    t: '2026-07-16T16:59:00',
                    count: 5,
                    topPhrases: [],
                },
            ],
        })

        expect(chapters).toContain('0:00:00 — chat spike (5 msgs)')
    })
})
