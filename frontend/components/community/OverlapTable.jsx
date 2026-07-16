'use client'
import Link from 'next/link'
import { Table } from 'react-bootstrap'
import { useOverlapTableModel } from '@/hooks/community/useOverlapTableModel'
import SortableTableHeader from '@/components/common/SortableTableHeader'

const COLUMNS = [
    {
        key: 'a',
        label: 'Creator A',
        align: 'start',
    },
    {
        key: 'b',
        label: 'Creator B',
        align: 'start',
    },
    {
        key: 'shared',
        label: 'Shared',
        align: 'end',
    },
    {
        key: 'jaccard',
        label: 'Jaccard',
        align: 'end',
    },
]

/**
 * Accessible table twin of the overlap heatmap: every pair as a sortable row.
 * Sorting is client-side (the endpoint returns the full top-N pair set at once).
 *
 * @param {object} props
 * @param {object} props.model
 */
const OverlapTable = ({ model }) => {
    const table = useOverlapTableModel({ rows: model.rows })

    return (
        <div
            role="region"
            aria-label="Overlap pairs"
        >
            <Table
                hover
                responsive
            >
                <thead>
                    <tr>
                        {COLUMNS.map(column => (
                            <SortableTableHeader
                                key={column.key}
                                column={column}
                                sort={table.sort}
                                dir={table.dir}
                                onSort={table.handleSort}
                            />
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {table.sortedRows.map(row => (
                        <tr
                            key={`${row.aId}-${row.bId}`}
                            className={model.isSelected(row.aId, row.bId) ? 'overlap-row is-selected' : 'overlap-row'}
                            onClick={() => model.onSelectPair(row.aId, row.bId)}
                            aria-selected={model.isSelected(row.aId, row.bId) || undefined}
                        >
                            <td><Link href={`/creator/${row.aId}`} onClick={event => event.stopPropagation()}>{row.aName}</Link></td>
                            <td><Link href={`/creator/${row.bId}`} onClick={event => event.stopPropagation()}>{row.bName}</Link></td>
                            <td className="mono text-end">{row.shared.toLocaleString()}</td>
                            <td className="mono text-end">
                                {row.jaccard == null ? '--' : `${(row.jaccard * 100).toFixed(1)}%`}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </Table>
        </div>
    )
}

export default OverlapTable
