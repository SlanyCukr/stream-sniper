import StreamMetricTile from './StreamMetricTile'
import { formatDecimal, formatInteger } from '@/utils/numberUtils'
import { formatClockTime } from '@/utils/dateUtils'

const percent = value => `${formatDecimal(value * 100)}%`

const METRICS = [
    { key: 'totalMessages', label: 'Total messages', format: formatInteger, phosphor: true },
    { key: 'messagesPerMinute', label: 'Messages / min', format: formatDecimal },
    { key: 'uniqueChatters', label: 'Unique chatters', format: formatInteger },
    { key: 'peakMessages', label: 'Peak minute', format: formatInteger },
    { key: 'newChatters', label: 'New chatters', format: formatInteger },
    { key: 'returningChatters', label: 'Returning chatters', format: formatInteger },
    { key: 'subShare', label: 'Sub share', format: percent },
    { key: 'avgViewers', label: 'Avg viewers', format: formatInteger },
    { key: 'peakViewers', label: 'Peak viewers', format: formatInteger, phosphor: true },
]

const DeltaChip = ({ deltaPct }) => {
    const direction = deltaPct > 0 ? 'up' : deltaPct < 0 ? 'down' : 'flat'
    const icon = { up: 'bi-arrow-up-right', down: 'bi-arrow-down-right', flat: 'bi-dash' }[direction]
    const text = `${deltaPct > 0 ? '+' : ''}${formatDecimal(deltaPct)}%`
    return (
        <span className={`report-delta is-${direction}`} aria-label={`${text} vs baseline median`}>
            <i className={`bi ${icon}`} aria-hidden="true" />{text}
        </span>
    )
}

export const hasReportContent = data => {
    const hasMetric = Object.values(data?.metrics || {}).some(metric => metric?.value != null)
    return hasMetric || Boolean(data?.topEmote || data?.topPhrase || data?.topMoments?.length)
}

const ReportMetricGrid = ({ data }) => {
    const tiles = METRICS.flatMap(definition => {
        const metric = data.metrics?.[definition.key]
        if (metric?.value == null) return []
        const percentile = metric.percentile != null
            ? [
                `P${formatDecimal(metric.percentile)}`,
                metric.baselineMedian != null
                    ? `vs median ${definition.format(metric.baselineMedian)}`
                    : null,
            ].filter(Boolean).join(' · ')
            : null
        const peak = definition.key === 'peakMessages' && data.peakBucketMinute
            ? `at ${formatClockTime(data.peakBucketMinute)}`
            : null
        return [{
            ...definition,
            metric,
            value: definition.format(metric.value),
            hint: [peak, percentile].filter(Boolean).join(' · ') || null,
        }]
    })

    if (tiles.length === 0) return null
    return (
        <div className="stat-grid mb-0" role="list" aria-label="Stream report metrics">
            {tiles.map(tile => (
                <StreamMetricTile
                    key={tile.key}
                    label={tile.label}
                    value={tile.value}
                    phosphor={tile.phosphor}
                    hint={tile.hint}
                >
                    {tile.metric.deltaPct != null ? <DeltaChip deltaPct={tile.metric.deltaPct} /> : null}
                </StreamMetricTile>
            ))}
        </div>
    )
}

const ReportHighlights = ({ data }) => {
    const moments = data.topMoments || []
    if (!data.topEmote && !data.topPhrase && moments.length === 0 && data.baselineCount < 2) {
        return null
    }
    return (
        <div className="report-highlights">
            {data.topEmote ? (
                <span className="report-chip">
                    <span className="report-chip-label">Top emote</span>
                    <span className="report-chip-value">{data.topEmote.name}</span>
                    <span className="report-chip-count mono">{formatInteger(data.topEmote.usageCount)}×</span>
                </span>
            ) : null}
            {data.topPhrase ? (
                <span className="report-chip">
                    <span className="report-chip-label">Top phrase</span>
                    <span className="report-chip-value">{data.topPhrase.phrase}</span>
                    <span className="report-chip-count mono">{formatInteger(data.topPhrase.usageCount)}×</span>
                </span>
            ) : null}
            {moments.map(moment => (
                <span key={moment.bucketMinute} className="report-chip">
                    <span className="report-chip-label">Moment</span>
                    <span className="report-chip-value mono">{formatClockTime(moment.bucketMinute)}</span>
                    <span className="report-chip-count mono">{formatInteger(moment.messageCount)} msgs</span>
                </span>
            ))}
            {data.baselineCount >= 2 ? (
                <span className="stat-hint report-baseline-note">
                    vs previous {data.baselineCount} streams
                </span>
            ) : null}
        </div>
    )
}

const StreamReportPresentation = ({ data }) => (
    <>
        <ReportMetricGrid data={data} />
        <ReportHighlights data={data} />
    </>
)

export default StreamReportPresentation
