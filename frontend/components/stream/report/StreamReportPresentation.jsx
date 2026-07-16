import StreamMetricTile from './StreamMetricTile'

const clock = timestamp => (
    typeof timestamp === 'string' && timestamp.length >= 16
        ? timestamp.slice(11, 16)
        : '--'
)
const integer = value => Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })
const decimal = value => Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
})
const percent = value => `${decimal(value * 100)}%`

const METRICS = [
    { key: 'totalMessages', label: 'Total messages', format: integer, phosphor: true },
    { key: 'messagesPerMinute', label: 'Messages / min', format: decimal },
    { key: 'uniqueChatters', label: 'Unique chatters', format: integer },
    { key: 'peakMessages', label: 'Peak minute', format: integer },
    { key: 'newChatters', label: 'New chatters', format: integer },
    { key: 'returningChatters', label: 'Returning chatters', format: integer },
    { key: 'subShare', label: 'Sub share', format: percent },
    { key: 'avgViewers', label: 'Avg viewers', format: integer },
    { key: 'peakViewers', label: 'Peak viewers', format: integer, phosphor: true },
]

const DeltaChip = ({ deltaPct }) => {
    const direction = deltaPct > 0 ? 'up' : deltaPct < 0 ? 'down' : 'flat'
    const icon = { up: 'bi-arrow-up-right', down: 'bi-arrow-down-right', flat: 'bi-dash' }[direction]
    const text = `${deltaPct > 0 ? '+' : ''}${decimal(deltaPct)}%`
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
                `P${decimal(metric.percentile)}`,
                metric.baselineMedian != null
                    ? `vs median ${definition.format(metric.baselineMedian)}`
                    : null,
            ].filter(Boolean).join(' · ')
            : null
        const peak = definition.key === 'peakMessages' && data.peakBucketMinute
            ? `at ${clock(data.peakBucketMinute)}`
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
                    <span className="report-chip-count mono">{integer(data.topEmote.usageCount)}×</span>
                </span>
            ) : null}
            {data.topPhrase ? (
                <span className="report-chip">
                    <span className="report-chip-label">Top phrase</span>
                    <span className="report-chip-value">{data.topPhrase.phrase}</span>
                    <span className="report-chip-count mono">{integer(data.topPhrase.usageCount)}×</span>
                </span>
            ) : null}
            {moments.map(moment => (
                <span key={moment.bucketMinute} className="report-chip">
                    <span className="report-chip-label">Moment</span>
                    <span className="report-chip-value mono">{clock(moment.bucketMinute)}</span>
                    <span className="report-chip-count mono">{integer(moment.messageCount)} msgs</span>
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
