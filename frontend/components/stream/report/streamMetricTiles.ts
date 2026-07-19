import { formatDurationHoursMinutes, formatDecimal, formatInteger } from '@/utils/numberUtils'
import { formatClockTime } from '@/utils/dateUtils'
import type { TimelineMetrics } from '@/hooks/stream/timeline/useStreamTimelineQuery'

const share = (part: number | null, total: number | null): string | null => (
    part == null || !total ? null : `${formatDecimal((part / total) * 100)}%`
)

export interface StreamMetricTileData {
    label: string
    value: string
    phosphor?: boolean
    hint?: string | null
}

export const buildStreamMetricTiles = (metrics: TimelineMetrics): StreamMetricTileData[] => {
    const tiles: StreamMetricTileData[] = [
        { label: 'Total messages', value: formatInteger(metrics.totalMessages), phosphor: true },
        { label: 'Messages / min', value: formatDecimal(metrics.msgsPerMin) },
        { label: 'Unique chatters', value: formatInteger(metrics.uniqueChatters) },
        {
            label: 'Peak minute',
            value: formatInteger(metrics.peakMessages),
            hint: metrics.peakAt ? `at ${formatClockTime(metrics.peakAt)}` : null,
        },
        { label: 'New chatters', value: formatInteger(metrics.newChatters) },
        { label: 'Returning chatters', value: formatInteger(metrics.returningChatters) },
        { label: 'Duration', value: formatDurationHoursMinutes(metrics.durationSec) },
    ]
    if (metrics.peakViewers != null) {
        tiles.push({ label: 'Peak viewers', value: formatInteger(metrics.peakViewers), phosphor: true })
    }
    const subShare = share(metrics.subMessages, metrics.totalMessages)
    if (subShare != null) {
        tiles.push({ label: 'Sub share', value: subShare, hint: `${formatInteger(metrics.subMessages)} sub msgs` })
    }
    const emoteShare = share(metrics.emoteMessages, metrics.totalMessages)
    if (emoteShare != null) {
        tiles.push({ label: 'Emote share', value: emoteShare, hint: `${formatInteger(metrics.emoteMessages)} emote msgs` })
    }
    return tiles
}
