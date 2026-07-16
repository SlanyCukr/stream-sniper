import { formatDurationHoursMinutes } from '@/utils/numberUtils'

const clock = timestamp => (
    typeof timestamp === 'string' && timestamp.length >= 16 ? timestamp.slice(11, 16) : '--'
)

const number = value => (value == null ? '--' : Number(value).toLocaleString())

const decimal = value => (value == null ? '--' : Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
}))

const share = (part, total) => (
    part == null || !total ? null : `${decimal((part / total) * 100)}%`
)

export const buildStreamMetricTiles = metrics => {
    const tiles = [
        { label: 'Total messages', value: number(metrics.totalMessages), phosphor: true },
        { label: 'Messages / min', value: decimal(metrics.msgsPerMin) },
        { label: 'Unique chatters', value: number(metrics.uniqueChatters) },
        {
            label: 'Peak minute',
            value: number(metrics.peakMessages),
            hint: metrics.peakAt ? `at ${clock(metrics.peakAt)}` : null,
        },
        { label: 'New chatters', value: number(metrics.newChatters) },
        { label: 'Returning chatters', value: number(metrics.returningChatters) },
        { label: 'Duration', value: formatDurationHoursMinutes(metrics.durationSec) },
    ]
    if (metrics.peakViewers != null) {
        tiles.push({ label: 'Peak viewers', value: number(metrics.peakViewers), phosphor: true })
    }
    const subShare = share(metrics.subMessages, metrics.totalMessages)
    if (subShare != null) {
        tiles.push({ label: 'Sub share', value: subShare, hint: `${number(metrics.subMessages)} sub msgs` })
    }
    const emoteShare = share(metrics.emoteMessages, metrics.totalMessages)
    if (emoteShare != null) {
        tiles.push({ label: 'Emote share', value: emoteShare, hint: `${number(metrics.emoteMessages)} emote msgs` })
    }
    return tiles
}
