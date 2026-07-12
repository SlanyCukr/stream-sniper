'use client'
import { useMemo, useState, useCallback } from 'react'

// Fixed-pixel geometry so axis <text> renders crisp (no preserveAspectRatio stretch).
// The whole SVG lives in an overflow-x:auto wrapper for small screens.
const CELL = 26
const LABEL_W = 132 // left gutter for row labels
const LABEL_H = 132 // top gutter for (vertical) column labels
const LABEL_MAX = 20 // truncate axis labels to N chars (+ <title> for the full name)

const truncate = (text, max = LABEL_MAX) => (
    text.length > max ? `${text.slice(0, max - 1)}…` : text
)

/**
 * SVG matrix heatmap of pairwise audience overlap. Creators sit on both axes,
 * sorted by the selected metric's audience desc. Cell intensity = a single-hue
 * ($phosphor) opacity ramp scaled to the pair's Jaccard for the selected metric;
 * a null Jaccard (zero union / not computed) renders as a hairline empty cell.
 *
 * Upper-triangle cells are keyboard focusable (HitColumns pattern); the lower
 * triangle mirrors them visually but is presentational — the table twin below
 * is the primary accessible path.
 *
 * @param {object} props
 * @param {Array} props.creators - [{creatorId, nick, displayName, chatters, regulars}]
 * @param {Array} props.pairs - [{a, b, sharedChatters, sharedRegulars, jaccardChatters, jaccardRegulars}]
 * @param {'chatters'|'regulars'} props.metric
 * @param {{aId:number,bId:number}|null} props.selectedPair
 * @param {function} props.onSelectPair - ({aId,bId}) => void
 */
const OverlapMatrix = ({
    creators, pairs, metric, selectedPair, onSelectPair,
}) => {
    const [
        hover,
        setHover,
    ] = useState(null)

    const nameOf = useCallback(c => c.displayName || c.nick || `#${c.creatorId}`, [
    ])

    // Sort creators by the selected metric's audience (desc), stable on id.
    const sorted = useMemo(() => {
        const audience = c => (metric === 'chatters' ? c.chatters : c.regulars) || 0
        return [
            ...creators,
        ].sort((a, b) => audience(b) - audience(a) || a.creatorId - b.creatorId)
    }, [
        creators,
        metric,
    ])

    // pairId "a-b" (a<b invariant) -> {shared, jaccard} for the selected metric.
    const lookup = useMemo(() => {
        const map = new Map()
        pairs.forEach(p => {
            map.set(`${p.a}-${p.b}`, {
                shared: metric === 'chatters' ? p.sharedChatters : p.sharedRegulars,
                jaccard: metric === 'chatters' ? p.jaccardChatters : p.jaccardRegulars,
            })
        })
        return map
    }, [
        pairs,
        metric,
    ])

    const cellFor = useCallback((rowId, colId) => {
        if (rowId === colId) {
            return null
        }
        const key = rowId < colId ? `${rowId}-${colId}` : `${colId}-${rowId}`
        return lookup.get(key) || { shared: 0, jaccard: null }
    }, [
        lookup,
    ])

    // Ramp denominator: brightest cell = the max non-null Jaccard in view.
    const maxJaccard = useMemo(() => {
        let max = 0
        lookup.forEach(v => {
            if (v.jaccard != null && v.jaccard > max) {
                max = v.jaccard
            }
        })
        return max
    }, [
        lookup,
    ])

    const n = sorted.length
    const width = LABEL_W + n * CELL
    const height = LABEL_H + n * CELL

    const fillOpacity = jaccard => {
        if (jaccard == null || maxJaccard <= 0) {
            return 0
        }
        // 0.08 floor keeps the lowest non-zero cell visible above $bg-surface.
        return 0.08 + 0.92 * Math.min(1, jaccard / maxJaccard)
    }

    const handleEnter = useCallback((i, j) => {
        const row = sorted[i]
        const col = sorted[j]
        const cell = cellFor(row.creatorId, col.creatorId)
        setHover({
            i,
            j,
            row,
            col,
            shared: cell?.shared ?? 0,
            jaccard: cell?.jaccard ?? null,
        })
    }, [
        sorted,
        cellFor,
    ])

    const handleLeave = useCallback(() => setHover(null), [
    ])

    const handleSelect = useCallback((rowId, colId) => {
        if (rowId === colId) {
            return
        }
        const aId = Math.min(rowId, colId)
        const bId = Math.max(rowId, colId)
        onSelectPair({ aId, bId })
    }, [
        onSelectPair,
    ])

    const isSelected = (rowId, colId) => {
        if (!selectedPair) {
            return false
        }
        const aId = Math.min(rowId, colId)
        const bId = Math.max(rowId, colId)
        return selectedPair.aId === aId && selectedPair.bId === bId
    }

    const tooltipLeft = hover ? LABEL_W + hover.j * CELL + CELL / 2 : 0
    const tooltipTop = hover ? LABEL_H + hover.i * CELL : 0

    return (
        <div className="overlap-matrix">
            <div className="overlap-scale" aria-hidden="true">
                <span className="overlap-scale-label">Low</span>
                <span className="overlap-scale-ramp" />
                <span className="overlap-scale-label">High Jaccard</span>
            </div>

            <div className="overlap-matrix-scroll">
                <div
                    className="overlap-matrix-inner"
                    style={{ width: `${width}px`, height: `${height}px` }}
                >
                    <svg
                        className="overlap-svg"
                        width={width}
                        height={height}
                        viewBox={`0 0 ${width} ${height}`}
                        role="img"
                        aria-label="Audience overlap matrix. Use the table below for a keyboard-friendly reading of every pair."
                    >
                        {/* Column labels (vertical, reading upward). */}
                        {sorted.map((c, j) => {
                            const cx = LABEL_W + j * CELL + CELL / 2
                            const cy = LABEL_H - 6
                            return (
                                <text
                                    key={`col-${c.creatorId}`}
                                    className={hover?.j === j ? 'overlap-axis-label is-active' : 'overlap-axis-label'}
                                    x={cx}
                                    y={cy}
                                    textAnchor="start"
                                    transform={`rotate(-90 ${cx} ${cy})`}
                                >
                                    {truncate(nameOf(c))}
                                    <title>{nameOf(c)}</title>
                                </text>
                            )
                        })}

                        {/* Row labels. */}
                        {sorted.map((c, i) => {
                            const ry = LABEL_H + i * CELL + CELL / 2
                            return (
                                <text
                                    key={`row-${c.creatorId}`}
                                    className={hover?.i === i ? 'overlap-axis-label is-active' : 'overlap-axis-label'}
                                    x={LABEL_W - 8}
                                    y={ry}
                                    textAnchor="end"
                                    dominantBaseline="middle"
                                >
                                    {truncate(nameOf(c))}
                                    <title>{nameOf(c)}</title>
                                </text>
                            )
                        })}

                        {/* Cells. */}
                        {sorted.map((row, i) => sorted.map((col, j) => {
                            const x = LABEL_W + j * CELL
                            const y = LABEL_H + i * CELL
                            const diagonal = i === j
                            const cell = diagonal ? null : cellFor(row.creatorId, col.creatorId)
                            const opacity = diagonal ? 0 : fillOpacity(cell?.jaccard)
                            const empty = !diagonal && (cell?.jaccard == null)
                            const focusable = !diagonal && i < j
                            const selected = !diagonal && isSelected(row.creatorId, col.creatorId)
                            const label = diagonal
                                ? undefined
                                : `${nameOf(row)} by ${nameOf(col)}: ${cell.jaccard == null
                                    ? 'no shared audience'
                                    : `${cell.shared.toLocaleString()} shared, ${(cell.jaccard * 100).toFixed(1)}% Jaccard`}`
                            return (
                                <g key={`${row.creatorId}-${col.creatorId}`}>
                                    <rect
                                        x={x + 0.5}
                                        y={y + 0.5}
                                        width={CELL - 1}
                                        height={CELL - 1}
                                        className={`overlap-cell${diagonal ? ' is-diagonal' : ''}${empty ? ' is-empty' : ''}${selected ? ' is-selected' : ''}`}
                                        fill="#9fef00"
                                        fillOpacity={opacity}
                                        role={focusable ? 'button' : undefined}
                                        tabIndex={focusable ? 0 : undefined}
                                        aria-hidden={focusable ? undefined : true}
                                        aria-label={focusable ? label : undefined}
                                        onMouseEnter={diagonal ? undefined : () => handleEnter(i, j)}
                                        onMouseLeave={diagonal ? undefined : handleLeave}
                                        onFocus={diagonal ? undefined : () => handleEnter(i, j)}
                                        onBlur={diagonal ? undefined : handleLeave}
                                        onClick={diagonal ? undefined : () => handleSelect(row.creatorId, col.creatorId)}
                                        onKeyDown={focusable ? event => {
                                            if (event.key === 'Enter' || event.key === ' ') {
                                                event.preventDefault()
                                                handleSelect(row.creatorId, col.creatorId)
                                            }
                                        } : undefined}
                                    >
                                        {label && <title>{label}</title>}
                                    </rect>
                                </g>
                            )
                        }))}
                    </svg>

                    {hover && (
                        <div
                            className="chart-tooltip overlap-tooltip"
                            style={{ left: `${tooltipLeft}px`, top: `${tooltipTop}px` }}
                        >
                            <span className="chart-tooltip-time">
                                {truncate(nameOf(hover.row), 24)} × {truncate(nameOf(hover.col), 24)}
                            </span>
                            <span className="chart-tooltip-metric">
                                {hover.shared.toLocaleString()} shared {metric}
                            </span>
                            <span className="chart-tooltip-metric">
                                {hover.jaccard == null
                                    ? 'Jaccard --'
                                    : `Jaccard ${(hover.jaccard * 100).toFixed(1)}%`}
                            </span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default OverlapMatrix
