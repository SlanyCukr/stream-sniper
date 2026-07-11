'use client'
import { useMemo, useState, useCallback } from 'react'
import { Table } from 'react-bootstrap'

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

const SortHeader = ({
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
                <span
                    className="th-sort-caret"
                    aria-hidden="true"
                >
                    {active ? (dir === 'asc' ? '▲' : '▼') : ''}
                </span>
            </button>
        </th>
    )
}

/**
 * Accessible table twin of the overlap heatmap: every pair as a sortable row.
 * Sorting is client-side (the endpoint returns the full top-N pair set at once).
 *
 * @param {object} props
 * @param {Array} props.creators
 * @param {Array} props.pairs
 * @param {'chatters'|'regulars'} props.metric
 * @param {{aId:number,bId:number}|null} props.selectedPair
 * @param {function} props.onSelectPair - ({aId,bId}) => void
 */
const OverlapTable = ({
    creators, pairs, metric, selectedPair, onSelectPair,
}) => {
    const [
        sort,
        setSort,
    ] = useState('jaccard')
    const [
        dir,
        setDir,
    ] = useState('desc')

    const nameMap = useMemo(() => {
        const map = new Map()
        creators.forEach(c => map.set(c.creatorId, c.displayName || c.nick || `#${c.creatorId}`))
        return map
    }, [
        creators,
    ])

    const rows = useMemo(() => pairs.map(p => ({
        aId: p.a,
        bId: p.b,
        aName: nameMap.get(p.a) || `#${p.a}`,
        bName: nameMap.get(p.b) || `#${p.b}`,
        shared: metric === 'chatters' ? p.sharedChatters : p.sharedRegulars,
        jaccard: metric === 'chatters' ? p.jaccardChatters : p.jaccardRegulars,
    })), [
        pairs,
        nameMap,
        metric,
    ])

    const sortedRows = useMemo(() => {
        const factor = dir === 'asc' ? 1 : -1
        const value = row => {
            if (sort === 'a') {
                return row.aName.toLowerCase()
            }
            if (sort === 'b') {
                return row.bName.toLowerCase()
            }
            if (sort === 'jaccard') {
                return row.jaccard
            }
            return row.shared
        }
        return [
            ...rows,
        ].sort((r1, r2) => {
            const v1 = value(r1)
            const v2 = value(r2)
            // null Jaccard (zero union) always sinks to the bottom, both directions.
            if (v1 == null && v2 == null) {
                return 0
            }
            if (v1 == null) {
                return 1
            }
            if (v2 == null) {
                return -1
            }
            if (v1 < v2) {
                return -1 * factor
            }
            if (v1 > v2) {
                return 1 * factor
            }
            return 0
        })
    }, [
        rows,
        sort,
        dir,
    ])

    const handleSort = useCallback(key => {
        if (sort === key) {
            setDir(prev => (prev === 'asc' ? 'desc' : 'asc'))
        } else {
            setSort(key)
            setDir(key === 'a' || key === 'b' ? 'asc' : 'desc')
        }
    }, [
        sort,
    ])

    const isSelected = row => (
        selectedPair && selectedPair.aId === row.aId && selectedPair.bId === row.bId
    )

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
                            <SortHeader
                                key={column.key}
                                column={column}
                                sort={sort}
                                dir={dir}
                                onSort={handleSort}
                            />
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {sortedRows.map(row => (
                        <tr
                            key={`${row.aId}-${row.bId}`}
                            className={isSelected(row) ? 'overlap-row is-selected' : 'overlap-row'}
                            onClick={() => onSelectPair({ aId: row.aId, bId: row.bId })}
                            aria-selected={isSelected(row) || undefined}
                        >
                            <td>{row.aName}</td>
                            <td>{row.bName}</td>
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
