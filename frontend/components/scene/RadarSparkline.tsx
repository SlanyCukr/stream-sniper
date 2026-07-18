'use client'

import type { RadarMinute } from '@/hooks/scene/useSceneRadarQuery'

export const SPARK_WIDTH = 120
export const SPARK_HEIGHT = 36
const BAR_GAP = 2

/**
 * Scale each per-minute message count to a bar height in [0, maxHeight], relative
 * to the busiest minute in the trace. A minute with zero messages maps to a
 * zero-height bar; an all-quiet trace (max ≤ 0) yields all zeros rather than a
 * divide-by-zero. Pure so the mapping is unit-testable without rendering.
 */
export const computeBarHeights = (
    minutes: Pick<RadarMinute, 'messages'>[],
    maxHeight = SPARK_HEIGHT,
): number[] => {
    const peak = minutes.reduce((max, minute) => Math.max(max, minute.messages), 0)
    if (peak <= 0) return minutes.map(() => 0)
    return minutes.map(minute => Math.round((Math.max(0, minute.messages) / peak) * maxHeight))
}

interface RadarSparklineProps {
    minutes: RadarMinute[]
    spiking: boolean
}

/**
 * Tiny inline-SVG bar chart of the trailing per-minute velocity (no chart lib).
 * The final bar is the current minute and is highlighted amber-red while the
 * channel is spiking; the rest render in phosphor.
 */
const RadarSparkline = ({ minutes, spiking }: RadarSparklineProps) => {
    const heights = computeBarHeights(minutes)
    const count = heights.length || 1
    const slot = SPARK_WIDTH / count
    const barWidth = Math.max(1, slot - BAR_GAP)
    const lastIndex = heights.length - 1

    return (
        <svg
            className="radar-spark"
            width={SPARK_WIDTH}
            height={SPARK_HEIGHT}
            viewBox={`0 0 ${SPARK_WIDTH} ${SPARK_HEIGHT}`}
            preserveAspectRatio="none"
            role="img"
            aria-label="Chat velocity, last 15 minutes"
        >
            {heights.map((height, index) => {
                const isCurrent = index === lastIndex
                const className = isCurrent && spiking
                    ? 'radar-spark-bar is-current is-spiking'
                    : isCurrent
                        ? 'radar-spark-bar is-current'
                        : 'radar-spark-bar'
                return (
                    <rect
                        key={minutes[index]?.minute ?? index}
                        className={className}
                        x={index * slot}
                        y={SPARK_HEIGHT - height}
                        width={barWidth}
                        height={height}
                    />
                )
            })}
        </svg>
    )
}

export default RadarSparkline
