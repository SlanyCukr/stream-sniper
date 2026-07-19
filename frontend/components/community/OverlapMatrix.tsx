'use client'
import {
    MATRIX_GEOMETRY,
    truncateMatrixLabel,
    useOverlapMatrixModel,
    type OverlapMatrixCreator,
} from '@/hooks/community/useOverlapMatrixModel'
import type { OverlapMatrixModel, OverlapCell as OverlapCellShape } from '@/hooks/community/useOverlapModel'
import type { OverlapMetric } from '@/hooks/community/useCommunityQuery'
import OverlapCell from './OverlapCell'

interface OverlapMatrixProps {
    creators: OverlapMatrixCreator[]
    metric: OverlapMetric
    model: OverlapMatrixModel
}

const OverlapMatrix = ({
    creators, metric, model: overlap,
}: OverlapMatrixProps) => {
    const model = useOverlapMatrixModel({
        creators, metric, model: overlap,
    })
    const {
        cell, labelWidth, labelHeight,
    } = MATRIX_GEOMETRY
    const width = labelWidth + model.sorted.length * cell
    const height = labelHeight + model.sorted.length * cell
    const tooltipLeft = model.hover
        ? labelWidth + model.hover.columnIndex * cell + cell / 2
        : 0
    const tooltipTop = model.hover ? labelHeight + model.hover.rowIndex * cell : 0

    const renderCell = (
        row: OverlapMatrixCreator,
        rowIndex: number,
        column: OverlapMatrixCreator,
        columnIndex: number,
    ) => {
        const diagonal = rowIndex === columnIndex
        const overlap: OverlapCellShape | null = diagonal ? null : model.cellFor(row.creatorId, column.creatorId)
        const focusable = !diagonal && rowIndex < columnIndex
        const selected = !diagonal && model.isSelected(row.creatorId, column.creatorId)
        const label = diagonal || !overlap
            ? undefined
            : `${model.nameOf(row)} by ${model.nameOf(column)}: ${overlap.jaccard == null
                ? 'no shared audience'
                : `${overlap.shared.toLocaleString()} shared, ${(overlap.jaccard * 100).toFixed(1)}% Jaccard`}`

        return (
            <OverlapCell
                key={`${row.creatorId}-${column.creatorId}`}
                x={labelWidth + columnIndex * cell + 0.5}
                y={labelHeight + rowIndex * cell + 0.5}
                size={cell - 1}
                diagonal={diagonal}
                empty={!diagonal && overlap?.jaccard == null}
                selected={selected}
                focusable={focusable}
                label={label}
                fillOpacity={diagonal ? 0 : model.fillOpacity(overlap?.jaccard ?? null)}
                onEnter={diagonal ? undefined : () => model.handleEnter(rowIndex, columnIndex)}
                onLeave={diagonal ? undefined : model.handleLeave}
                onSelect={diagonal
                    ? undefined
                    : () => model.handleSelect(row.creatorId, column.creatorId)}
            />
        )
    }

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
                    style={{ width: `${width}px`, height: `${height}px` }}>
                    <svg
                        className="overlap-svg"
                        width={width}
                        height={height}
                        viewBox={`0 0 ${width} ${height}`}
                        role="img"
                        aria-label="Audience overlap matrix. Use the table below for a keyboard-friendly reading of every pair.">
                        {model.sorted.map((creator, columnIndex) => {
                            const x = labelWidth + columnIndex * cell + cell / 2
                            const y = labelHeight - 6
                            return (
                                <text
                                    key={`column-${creator.creatorId}`}
                                    className={model.hover?.columnIndex === columnIndex ? 'overlap-axis-label is-active' : 'overlap-axis-label'}
                                    x={x}
                                    y={y}
                                    textAnchor="start"
                                    transform={`rotate(-90 ${x} ${y})`}>
                                    {truncateMatrixLabel(model.nameOf(creator))}
                                    <title>{model.nameOf(creator)}</title>
                                </text>
                            )
                        })}
                        {model.sorted.map((creator, rowIndex) => (
                            <text
                                key={`row-${creator.creatorId}`}
                                className={model.hover?.rowIndex === rowIndex ? 'overlap-axis-label is-active' : 'overlap-axis-label'}
                                x={labelWidth - 8}
                                y={labelHeight + rowIndex * cell + cell / 2}
                                textAnchor="end"
                                dominantBaseline="middle">
                                {truncateMatrixLabel(model.nameOf(creator))}
                                <title>{model.nameOf(creator)}</title>
                            </text>
                        ))}
                        {model.sorted.map((row, rowIndex) => model.sorted.map(
                            (column, columnIndex) => renderCell(
                                row,
                                rowIndex,
                                column,
                                columnIndex,
                            ),
                        ))}
                    </svg>

                    {model.hover ? (
                        <div
                            className="chart-tooltip overlap-tooltip"
                            style={{ left: `${tooltipLeft}px`, top: `${tooltipTop}px` }}>
                            <span className="chart-tooltip-time">
                                {truncateMatrixLabel(model.nameOf(model.hover.row), 24)} ×{' '}
                                {truncateMatrixLabel(model.nameOf(model.hover.column), 24)}
                            </span>
                            <span className="chart-tooltip-metric">
                                {model.hover.shared.toLocaleString()} shared {metric}
                            </span>
                            <span className="chart-tooltip-metric">
                                {model.hover.jaccard == null
                                    ? 'Jaccard --'
                                    : `Jaccard ${(model.hover.jaccard * 100).toFixed(1)}%`}
                            </span>
                        </div>
                    ) : null}
                </div>
            </div>
        </div>
    )
}

export default OverlapMatrix
