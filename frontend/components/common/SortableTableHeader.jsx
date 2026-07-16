const SortableTableHeader = ({
    column, sort, dir, onSort,
}) => {
    const active = sort === column.key
    return (
        <th
            scope="col"
            className={column.align === 'end' ? 'text-end' : undefined}
            aria-sort={active ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'}
        >
            <button
                type="button"
                className={active ? 'th-sort active' : 'th-sort'}
                onClick={() => onSort(column.key)}
            >
                {column.label}
                <span className="th-sort-caret" aria-hidden="true">
                    {active ? (dir === 'asc' ? '▲' : '▼') : ''}
                </span>
            </button>
        </th>
    )
}

export default SortableTableHeader
