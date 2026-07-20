'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import Select from 'react-select'
import { Card, Table } from 'react-bootstrap'
import { useStreamComparison, type StreamComparisonStream } from '@/hooks/stream/useStreamComparisonQuery'
import { useStreams, type StreamListRow } from '@/hooks/stream/list/useStreamsQuery'
import EmptyState from '@/components/common/EmptyState'
import QueryState from '@/components/common/QueryState'

const COLORS = ['#69f0ae', '#ffb74d', '#64b5f6', '#ef9a9a']

type NumericMetricKey = 'totalMessages' | 'messagesPerMinute' | 'uniqueChatters' | 'newChatters'
    | 'returningChatters' | 'peakViewers' | 'subShare' | 'emoteShare'

const metrics: [string, NumericMetricKey, (value: number | null) => string][] = [
    ['Total messages', 'totalMessages', value => value?.toLocaleString?.() ?? '--'],
    ['Messages/min', 'messagesPerMinute', value => value == null ? '--' : value.toFixed(1)],
    ['Unique chatters', 'uniqueChatters', value => value?.toLocaleString?.() ?? '--'],
    ['New chatters', 'newChatters', value => value?.toLocaleString?.() ?? '--'],
    ['Returning', 'returningChatters', value => value?.toLocaleString?.() ?? '--'],
    ['Peak viewers', 'peakViewers', value => value?.toLocaleString?.() ?? '--'],
    ['Subscriber share', 'subShare', value => value == null ? '--' : `${Math.round(value * 100)}%`],
    ['Emote share', 'emoteShare', value => value == null ? '--' : `${Math.round(value * 100)}%`],
]

interface StreamOption {
    value: number
    label: string
}

export const buildStreamOptions = (
    page: { items?: StreamListRow[] } | undefined,
    initialIds: number[],
): StreamOption[] => {
    const options: StreamOption[] = (page?.items || []).map(stream => ({
        value: stream.streamId,
        label: `${stream.creatorName} · ${stream.start} · #${stream.streamId}`,
    }))
    initialIds.forEach(id => {
        if (!options.some(option => option.value === id)) {
            options.push({ value: id, label: `Stream #${id}` })
        }
    })
    return options
}

const CurveChart = ({ streams }: { streams: StreamComparisonStream[] }) => {
    const max = Math.max(1, ...streams.flatMap(stream => stream.curve.map(point => point.messageCount)))
    return (
        <div className="compare-chart-wrap">
            <svg
                className="compare-chart"
                viewBox="0 0 800 260"
                role="img"
                aria-label="Normalized chat activity curves"
            >
                {[0, 25, 50, 75, 100].map(percent => (
                    <g key={percent}>
                        <line
                            x1={percent * 8}
                            x2={percent * 8}
                            y1="0"
                            y2="230"
                            className="compare-grid-line"
                        />
                        <text
                            x={percent * 8}
                            y="252"
                            textAnchor="middle"
                        >
                            {`${percent}%`}
                        </text>
                    </g>
                ))}
                {streams.map((stream, index) => (
                    <polyline
                        key={stream.streamId}
                        fill="none"
                        stroke={COLORS[index]}
                        strokeWidth="3"
                        points={stream.curve.map(point => `${point.percent * 8},${225 - point.messageCount * 215 / max}`).join(' ')}
                    />
                ))}
            </svg>
            <div className="compare-legend">
                {streams.map((stream, index) => (
                    <span key={stream.streamId}>
                        <i style={{ background: COLORS[index] }} />
                        {`${stream.creatorDisplayName} · #${stream.streamId}`}
                    </span>
                ))}
            </div>
        </div>
    )
}

interface StreamCompareProps {
    initialIds?: number[]
}

const StreamCompare = ({ initialIds = [] }: StreamCompareProps) => {
    const [selectedIds, setSelectedIds] = useState<number[]>(initialIds)
    const streamsQuery = useStreams({ sort: 'start', dir: 'desc' })
    const options = useMemo(
        () => buildStreamOptions(streamsQuery.data, initialIds),
        [streamsQuery.data, initialIds],
    )
    const selected = options.filter(option => selectedIds.includes(option.value))
    const comparison = useStreamComparison(selectedIds)

    return (
        <>
            <header className="page-head">
                <div>
                    <p className="page-sub">
                        normalized side-by-side analytics
                    </p>
                    <h1 className="page-title">
                        Stream comparison
                    </h1>
                </div>
            </header>
            <div className="toolbar compare-toolbar">
                <label
                    className="visually-hidden"
                    htmlFor="compare-streams"
                >
                    Choose streams
                </label>
                <Select
                    classNamePrefix="rs"
                    instanceId="compare-streams"
                    inputId="compare-streams"
                    isMulti
                    options={options}
                    value={selected}
                    onChange={items => setSelectedIds(items.slice(0, 4).map(item => item.value))}
                    placeholder="Choose 2–4 recent streams..."
                />
                <span className="toolbar-readout">
                    {`${selectedIds.length}/4 selected`}
                </span>
            </div>

            {selectedIds.length < 2 ? (
                <EmptyState title="Choose at least two streams" />
            ) : null}
            <QueryState
                query={comparison}
                errorTitle="Comparison failed"
                loadingText="Comparing streams..."
                isEmpty={value => (value?.streams || []).length < 2}
                emptyState={null}
                showErrorDetails={false}
            >
                {value => (
                    <>
                        <Card>
                            <Card.Body>
                                <div className="section-label">
                                    Chat activity by stream progress
                                </div>
                                <CurveChart streams={value.streams} />
                            </Card.Body>
                        </Card>
                        <Card className="mt-3">
                            <Card.Body className="p-0">
                                <Table
                                    responsive
                                    hover
                                    className="mb-0 compare-table"
                                >
                                    <thead>
                                        <tr>
                                            <th>Metric</th>
                                            {value.streams.map(stream => (
                                                <th key={stream.streamId}>
                                                    <Link href={`/stream/${stream.streamId}`}>
                                                        {stream.creatorDisplayName}
                                                        <br />
                                                        <small>{stream.title}</small>
                                                    </Link>
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {metrics.map(([label, key, format]) => (
                                            <tr key={key}>
                                                <th>{label}</th>
                                                {value.streams.map(stream => (
                                                    <td
                                                        className="mono"
                                                        key={stream.streamId}
                                                    >
                                                        {format(stream[key])}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </Table>
                            </Card.Body>
                        </Card>
                        <div className="retention-strip">
                            {(value.retention || []).map(item => (
                                <Card key={`${item.fromStreamId}-${item.toStreamId}`}>
                                    <Card.Body>
                                        <div className="section-label">
                                            {`#${item.fromStreamId} → #${item.toStreamId}`}
                                        </div>
                                        <div className="stat-value">
                                            {item.retentionRate == null ? '--' : `${Math.round(item.retentionRate * 100)}%`}
                                        </div>
                                        <div className="stat-hint">
                                            {`${item.retained} of ${item.fromAudience} chatters returned`}
                                        </div>
                                    </Card.Body>
                                </Card>
                            ))}
                        </div>
                    </>
                )}
            </QueryState>
        </>
    )
}

export default StreamCompare
