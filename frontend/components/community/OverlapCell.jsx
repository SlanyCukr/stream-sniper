const OverlapCell = ({
    x,
    y,
    size,
    diagonal,
    empty,
    selected,
    focusable,
    label,
    fillOpacity,
    onEnter,
    onLeave,
    onSelect,
}) => {
    const handleKeyDown = event => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            onSelect?.()
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
            onMouseEnter={onEnter}
            onMouseLeave={onLeave}
            onFocus={onEnter}
            onBlur={onLeave}
            onClick={onSelect}
            onKeyDown={focusable ? handleKeyDown : undefined}>
            {label ? <title>{label}</title> : null}
        </rect>
    )
}

export default OverlapCell
