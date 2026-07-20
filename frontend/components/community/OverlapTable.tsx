'use client'
import Link from 'next/link'
import { Table } from 'react-bootstrap'
import { useOverlapTableModel } from '@/hooks/community/useOverlapTableModel'
import type { OverlapTableModel } from '@/hooks/community/useOverlapModel'
import SortableTableHeader from '@/components/common/SortableTableHeader'
import { formatSharePct } from '@/utils/numberUtils'

interface OverlapTableColumn {
    key: 'a' | 'b' | 'shared' | 'jaccard'
    label: string
    align: 'start' | 'end'
}

const COLUMNS: OverlapTableColumn[] = [
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

interface OverlapTableProps {
    model: OverlapTableModel
}

/**
 * Accessible table twin of the overlap heatmap: every pair as a sortable row.
 * Sorting is client-side (the endpoint returns the full top-N pair set at once).
 */
const OverlapTable = ({ model }: OverlapTableProps) => {
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
                                {row.jaccard == null ? '--' : formatSharePct(row.jaccard)}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </Table>
        </div>
    )
}

export default OverlapTable
