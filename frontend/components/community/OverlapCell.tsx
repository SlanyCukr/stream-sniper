import { memo, type KeyboardEvent } from 'react'

interface OverlapCellProps {
    x: number
    y: number
    size: number
    diagonal: boolean
    empty?: boolean
    selected: boolean
    focusable: boolean
    label?: string
    fillOpacity: number
    /** Sorted-matrix coordinates / creator ids, passed back to the stable handlers. */
    rowIndex: number
    columnIndex: number
    rowId: number
    columnId: number
    onEnter?: (rowIndex: number, columnIndex: number) => void
    onLeave?: () => void
    onSelect?: (rowId: number, columnId: number) => void
}

/**
 * One matrix cell. Memoized with identity-stable handlers (coordinates travel
 * as data props) so a hover transition re-renders only the affected cells, not
 * all N² of them.
 */
const OverlapCell = memo(({
    x,
    y,
    size,
    diagonal,
    empty,
    selected,
    focusable,
    label,
    fillOpacity,
    rowIndex,
    columnIndex,
    rowId,
    columnId,
    onEnter,
    onLeave,
    onSelect,
}: OverlapCellProps) => {
    const enter = onEnter ? () => onEnter(rowIndex, columnIndex) : undefined
    const select = onSelect ? () => onSelect(rowId, columnId) : undefined
    const handleKeyDown = (event: KeyboardEvent<SVGRectElement>) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            select?.()
        }
    }

    return (
        <rect
            x={x}
            y={y}
            width={size}
            height={size}
            className={`overlap-cell${diagonal ? ' is-diagonal' : ''}${empty ? ' is-empty' : ''}${selected ? ' is-selected' : ''}`}
            fill="#9fef00"
            fillOpacity={fillOpacity}
            role={focusable ? 'button' : undefined}
            tabIndex={focusable ? 0 : undefined}
            aria-hidden={focusable ? undefined : true}
            aria-label={focusable ? label : undefined}
            onMouseEnter={enter}
            onMouseLeave={onLeave}
            onFocus={enter}
            onBlur={onLeave}
            onClick={select}
            onKeyDown={focusable ? handleKeyDown : undefined}>
            {label ? <title>{label}</title> : null}
        </rect>
    )
})

OverlapCell.displayName = 'OverlapCell'

export default OverlapCell
