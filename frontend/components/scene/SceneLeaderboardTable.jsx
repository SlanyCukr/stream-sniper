'use client'
import {
    useMemo,
} from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { Card, Table } from 'react-bootstrap'
import SortableTableHeader from '@/components/common/SortableTableHeader'
import { useTableSort } from '@/hooks/useTableSort'
import { compareNullable } from '@/utils/sortUtils'

const formatNumber = (value, digits = 0) => {
    if (value == null) {
        return '--'
    }
    return digits > 0 ? value.toFixed(digits) : value.toLocaleString()
}

const renderCreator = entry => (
    <Link className="scene-streamer" href={`/creator/${entry.creatorId}`}>
        {entry.profileImageUrl ? (
            <Image
                className="scene-avatar"
                src={entry.profileImageUrl}
                alt=""
                width={28}
                height={28}
            />
        ) : (
            <span className="scene-avatar scene-avatar-empty" aria-hidden="true" />
        )}
        <span className="scene-streamer-name">
            {entry.displayName || entry.nick}
        </span>
    </Link>
)

const numericColumn = (key, label, digits = 0) => ({
    key,
    label,
    align: 'end',
    cellClassName: 'mono text-end',
    render: entry => formatNumber(entry[key], digits),
})

const COLUMNS = [
    {
        key: 'rank',
        label: '#',
        align: 'start',
        cellClassName: 'rank-num',
        render: entry => String(entry.rank).padStart(2, '0'),
    },
    {
        key: 'name',
        label: 'Streamer',
        align: 'start',
        render: renderCreator,
    },
    numericColumn('streams', 'Streams'),
    numericColumn('hoursStreamed', 'Hours', 1),
    numericColumn('totalMessages', 'Messages'),
    numericColumn('msgsPerMin', 'Msgs/min', 1),
    numericColumn('chatterAppearances', 'Chatter appearances'),
    numericColumn('peakViewers', 'Peak viewers'),
]

const sortValue = (row, key) => (
    key === 'name'
        ? (row.displayName || row.nick || '').toLowerCase()
        : row[key]
)

const compareRows = (first, second, sort, dir) => {
    const firstValue = sortValue(first, sort)
    const secondValue = sortValue(second, sort)
    return compareNullable(firstValue, secondValue, dir)
}

const defaultSortDirection = key => (
    key === 'name' || key === 'rank' ? 'asc' : 'desc'
)

const SceneLeaderboardTable = ({ entries }) => {
    const { sort, dir, onSort } = useTableSort({
        initialKey: 'rank',
        initialDirection: 'asc',
        getDefaultDirection: defaultSortDirection,
    })

    const sortedEntries = useMemo(() => (
        [...entries].sort((first, second) => compareRows(first, second, sort, dir))
    ), [
        entries,
        sort,
        dir,
    ])

    return (
        <Card>
            <Card.Body className="p-0">
                <div role="region" aria-label="Scene leaderboard">
                    <Table hover responsive className="mb-0">
                        <thead>
                            <tr>
                                {COLUMNS.map(column => (
                                    <SortableTableHeader
                                        key={column.key}
                                        column={column}
                                        sort={sort}
                                        dir={dir}
                                        onSort={onSort}
                                    />
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {sortedEntries.map(entry => (
                                <tr key={entry.creatorId}>
                                    {COLUMNS.map(column => (
                                        <td key={column.key} className={column.cellClassName}>
                                            {column.render(entry)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                </div>
            </Card.Body>
        </Card>
    )
}

export default SceneLeaderboardTable
