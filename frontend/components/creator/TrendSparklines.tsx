import type { KeyboardEvent, ReactNode } from 'react'
import { formatDurationHoursMinutes } from '@/utils/numberUtils'
import type { CreatorTrendPoint } from '@/hooks/creator/useCreatorTrendsQuery'

const WIDTH = 240
const HEIGHT = 56
const PAD_X = 6
const PAD_TOP = 6
const PAD_BOTTOM = 8

const xFor = (index: number, count: number): number => (
    count <= 1
        ? WIDTH / 2
        : PAD_X + (index * (WIDTH - 2 * PAD_X)) / (count - 1)
)

export const formatTrendDuration = formatDurationHoursMinutes

interface SparkStreamsProps {
    streams: CreatorTrendPoint[]
    onStreamSelect: (streamId: number) => void
    getStreamLabel: (stream: CreatorTrendPoint) => string
}

const HitColumns = ({
    streams, onStreamSelect, getStreamLabel,
}: SparkStreamsProps) => {
    const count = streams.length
    const columnWidth = count <= 1
        ? WIDTH - 2 * PAD_X
        : (WIDTH - 2 * PAD_X) / count

    return streams.map((stream, index) => {
        const centerX = xFor(index, count)
        const hitX = count <= 1 ? PAD_X : PAD_X + index * columnWidth
        const label = getStreamLabel(stream)
        return (
            <g key={stream.streamId}>
                <rect
                    className="spark-hit"
                    x={hitX}
                    y={0}
                    width={columnWidth}
                    height={HEIGHT}
                    role="link"
                    tabIndex={0}
                    aria-label={label}
                    onClick={() => onStreamSelect(stream.streamId)}
                    onKeyDown={(event: KeyboardEvent<SVGRectElement>) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault()
                            onStreamSelect(stream.streamId)
                        }
                    }}>
                    <title>{label}</title>
                </rect>
                <line
                    className="spark-hit-marker"
                    x1={centerX}
                    y1={PAD_TOP - 4}
                    x2={centerX}
                    y2={HEIGHT}
                />
            </g>
        )
    })
}

interface SparkFrameProps extends SparkStreamsProps {
    children: ReactNode
}

const SparkFrame = ({
    streams, onStreamSelect, getStreamLabel, children,
}: SparkFrameProps) => (
    <svg
        className="trend-spark"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none">
        {children}
        <HitColumns {...{ streams, onStreamSelect, getStreamLabel }} />
    </svg>
)

interface BarLayout {
    barWidth: number
    baselineY: number
    centerX: (index: number) => number
    heightFor: (value: number) => number
}

const createBarLayout = (values: (number | null)[]): BarLayout => {
    const count = values.length
    const max = Math.max(1, ...values.filter((value): value is number => value != null))
    const slot = count <= 1 ? WIDTH - 2 * PAD_X : (WIDTH - 2 * PAD_X) / count
    const scale = HEIGHT - PAD_TOP - PAD_BOTTOM
    return {
        barWidth: Math.max(2, slot * 0.55),
        baselineY: HEIGHT - PAD_BOTTOM,
        centerX: index => (count <= 1 ? WIDTH / 2 : PAD_X + slot * index + slot / 2),
        heightFor: value => (value / max) * scale,
    }
}

interface AreaSparkProps {
    streams: CreatorTrendPoint[]
    values: (number | null)[]
    onStreamSelect: (streamId: number) => void
    getStreamLabel: (stream: CreatorTrendPoint) => string
}

interface SparkPoint {
    x: number
    y: number
}

export const AreaSpark = ({
    streams, values, onStreamSelect, getStreamLabel,
}: AreaSparkProps) => {
    const max = Math.max(1, ...values.filter((value): value is number => value != null))
    const yFor = (value: number): number => (
        HEIGHT - PAD_BOTTOM - (value / max) * (HEIGHT - PAD_TOP - PAD_BOTTOM)
    )
    const segments: SparkPoint[][] = []
    let current: SparkPoint[] = []

    values.forEach((value, index) => {
        if (value == null) {
            if (current.length) {
                segments.push(current)
            }
            current = []
            return
        }
        current.push({
            x: xFor(index, values.length),
            y: yFor(value),
        })
    })
    if (current.length) {
        segments.push(current)
    }

    return (
        <SparkFrame {...{ streams, onStreamSelect, getStreamLabel }}>
            {segments.map((segment, index) => {
                const line = segment
                    .map((point, pointIndex) => `${pointIndex === 0 ? 'M' : 'L'}${point.x},${point.y}`)
                    .join(' ')
                const area = segment.length > 1
                    // non-null: segment.length > 1 guarantees a last element
                    ? `${line} L${segment.at(-1)!.x},${HEIGHT - PAD_BOTTOM} L${segment[0].x},${HEIGHT - PAD_BOTTOM} Z`
                    : null
                return (
                    <g key={index}>
                        {area ? <path className="spark-area-fill" d={area} /> : null}
                        <path className="spark-area-line" d={line} />
                    </g>
                )
            })}
        </SparkFrame>
    )
}

interface BarSparkProps {
    streams: CreatorTrendPoint[]
    values: (number | null)[]
    onStreamSelect: (streamId: number) => void
    getStreamLabel: (stream: CreatorTrendPoint) => string
    className?: string
}

export const BarSpark = ({
    streams, values, onStreamSelect, getStreamLabel, className = 'spark-bar',
}: BarSparkProps) => {
    const layout = createBarLayout(values)

    return (
        <SparkFrame {...{ streams, onStreamSelect, getStreamLabel }}>
            {values.map((value, index) => {
                if (value == null) {
                    return null
                }
                const height = layout.heightFor(value)
                return (
                    <rect
                        key={streams[index].streamId}
                        className={className}
                        x={layout.centerX(index) - layout.barWidth / 2}
                        y={layout.baselineY - height}
                        width={layout.barWidth}
                        height={Math.max(0.5, height)}
                    />
                )
            })}
        </SparkFrame>
    )
}

export const StackSpark = ({
    streams, onStreamSelect, getStreamLabel,
}: SparkStreamsProps) => {
    const totals: (number | null)[] = streams.map(stream => {
        if (stream.returningChatters == null && stream.newChatters == null) {
            return null
        }
        return (stream.returningChatters || 0) + (stream.newChatters || 0)
    })
    const layout = createBarLayout(totals)

    return (
        <SparkFrame {...{ streams, onStreamSelect, getStreamLabel }}>
            {streams.map((stream, index) => {
                if (totals[index] == null) {
                    return null
                }
                const returningHeight = layout.heightFor(stream.returningChatters || 0)
                const newHeight = layout.heightFor(stream.newChatters || 0)
                return (
                    <g key={stream.streamId}>
                        <rect
                            className="spark-bar spark-bar--returning"
                            x={layout.centerX(index) - layout.barWidth / 2}
                            y={layout.baselineY - returningHeight}
                            width={layout.barWidth}
                            height={Math.max(0, returningHeight)}
                        />
                        <rect
                            className="spark-bar spark-bar--new"
                            x={layout.centerX(index) - layout.barWidth / 2}
                            y={layout.baselineY - returningHeight - newHeight}
                            width={layout.barWidth}
                            height={Math.max(0, newHeight)}
                        />
                    </g>
                )
            })}
        </SparkFrame>
    )
}
