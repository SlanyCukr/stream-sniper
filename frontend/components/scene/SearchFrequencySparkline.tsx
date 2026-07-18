'use client'

import type { SearchFrequencyPoint } from './searchTypes'

const WIDTH = 320
const HEIGHT = 60
const PAD_X = 4
const PAD_TOP = 6
const PAD_BOTTOM = 6

const xFor = (index: number, count: number) => (
  count <= 1 ? WIDTH / 2 : PAD_X + (index * (WIDTH - 2 * PAD_X)) / (count - 1)
)

interface SearchFrequencySparklineProps {
  points: SearchFrequencyPoint[]
}

/**
 * Minimal single-series frequency sparkline (count per day). Inline SVG styled
 * with the shared night-ops `.trend-spark` chart classes; each day exposes a
 * `<title>` tooltip. Oldest-first, zero-filled points come straight from the
 * `/search/frequency` contract.
 */
const SearchFrequencySparkline = ({ points }: SearchFrequencySparklineProps) => {
  if (points.length === 0) return null

  const counts = points.map(point => point.count)
  const max = Math.max(1, ...counts)
  const total = counts.reduce((sum, value) => sum + value, 0)
  const yFor = (value: number) => (
    HEIGHT - PAD_BOTTOM - (value / max) * (HEIGHT - PAD_TOP - PAD_BOTTOM)
  )

  const line = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${xFor(index, points.length)},${yFor(point.count)}`)
    .join(' ')
  const area = points.length > 1
    ? `${line} L${xFor(points.length - 1, points.length)},${HEIGHT - PAD_BOTTOM} L${xFor(0, points.length)},${HEIGHT - PAD_BOTTOM} Z`
    : null
  const columnWidth = points.length <= 1
    ? WIDTH - 2 * PAD_X
    : (WIDTH - 2 * PAD_X) / points.length

  return (
    <figure className="search-frequency">
      <figcaption className="search-frequency-caption">
        {`${total.toLocaleString()} matches over ${points.length} days`}
      </figcaption>
      <svg
        className="trend-spark"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`Match frequency: ${total.toLocaleString()} matches across ${points.length} days`}
      >
        {area ? <path className="spark-area-fill" d={area} /> : null}
        <path className="spark-area-line" d={line} />
        {points.map((point, index) => (
          <rect
            key={point.date}
            className="spark-hit"
            x={points.length <= 1 ? PAD_X : PAD_X + index * columnWidth}
            y={0}
            width={columnWidth}
            height={HEIGHT}
          >
            <title>{`${point.date}: ${point.count.toLocaleString()} matches`}</title>
          </rect>
        ))}
      </svg>
    </figure>
  )
}

export default SearchFrequencySparkline
