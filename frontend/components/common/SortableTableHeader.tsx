import type { ReactNode } from 'react'
import type { SortDirection } from '@/hooks/useTableSort'

interface SortableColumn<K extends string> {
    key: K
    label: ReactNode
    align?: 'start' | 'end'
}

interface SortableTableHeaderProps<K extends string> {
    column: SortableColumn<K>
    sort: K
    dir: SortDirection
    onSort: (key: K) => void
}

const SortableTableHeader = <K extends string>({
    column, sort, dir, onSort,
}: SortableTableHeaderProps<K>) => {
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
