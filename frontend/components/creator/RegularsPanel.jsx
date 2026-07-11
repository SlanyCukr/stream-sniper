'use client'
import { useState, useCallback } from 'react'
import { Card, Table } from 'react-bootstrap'
import { useCreatorRegulars } from '@/hooks/useApiQuery'
import { formatTimeAgo } from '@/utils/dateUtils'
import { DEFAULT_MIN_STREAMS } from '@/constants'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

const REGULARS_LIMIT = 50

// Sortable columns → server-side `sort` keys (attendance|streams|last_seen|messages).
const SORTABLE_COLUMNS = [
    {
        key: 'streams',
        label: 'Streams attended',
        align: 'start',
    },
    {
        key: 'attendance',
        label: 'Attendance rate',
        align: 'end',
    },
    {
        key: 'last_seen',
        label: 'Last seen',
        align: 'end',
    },
    {
        key: 'messages',
        label: 'Messages',
        align: 'end',
    },
]

/**
 * Sortable table header button (server-side sort). Toggles direction when re-clicked.
 */
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
 * Creator "regulars" v2: sortable, min-streams-filtered table of recurring chatters.
 * @param {object} props
 * @param {number|null} props.creatorId
 */
const RegularsPanel = ({ creatorId }) => {
    const [
        sort,
        setSort,
    ] = useState('attendance')
    const [
        dir,
        setDir,
    ] = useState('desc')
    const [
        minStreams,
        setMinStreams,
    ] = useState(DEFAULT_MIN_STREAMS)

    const {
        data,
        isLoading,
        error,
        refetch,
    } = useCreatorRegulars(creatorId, {
        minStreams,
        sort,
        dir,
        limit: REGULARS_LIMIT,
    })

    const regulars = data?.regulars || []
    const totalStreams = data?.totalStreams || 0

    /** Toggle direction when re-clicking the active column, else sort desc on the new one. */
    const handleSort = useCallback(key => {
        if (sort === key) {
            setDir(prevDir => (prevDir === 'asc' ? 'desc' : 'asc'))
        } else {
            setSort(key)
            setDir('desc')
        }
    }, [
        sort,
    ])

    const handleMinStreamsChange = useCallback(event => {
        const value = Number.parseInt(event.target.value, 10)
        setMinStreams(Number.isNaN(value) || value < 1 ? 1 : value)
    }, [
    ])

    if (!creatorId) {
        return (
            <Card>
                <Card.Body className="p-0">
                    <div className="empty-state">
                        <div
                            className="empty-scope"
                            aria-hidden="true" />
                        <p className="empty-title">No creator selected</p>
                        <p className="empty-hint">
                            Select a creator to see their most loyal chatters across all captured streams.
                        </p>
                    </div>
                </Card.Body>
            </Card>
        )
    }

    return (
        <>
            <div className="regulars-controls">
                <label htmlFor="regulars-min-streams">Min streams attended</label>
                <input
                    id="regulars-min-streams"
                    type="number"
                    min={1}
                    className="form-control form-control-sm regulars-min-input"
                    value={minStreams}
                    onChange={handleMinStreamsChange}
                />
                {!isLoading && !error && (
                    <span className="toolbar-readout">
                        <strong>{regulars.length}</strong> regulars of <strong>{totalStreams}</strong> streams
                    </span>
                )}
            </div>

            <Card>
                <Card.Body className={isLoading || error || regulars.length === 0 ? 'p-0' : ''}>
                    {isLoading && (
                        <LoadingSpinner
                            size="lg"
                            text="Loading regulars..."
                        />
                    )}

                    {error && (
                        <ErrorAlert
                            error={error}
                            title="Failed to load regulars"
                            onRetry={refetch}
                            showDetails={process.env.NODE_ENV === 'development'}
                        />
                    )}

                    {!isLoading && !error && regulars.length === 0 && (
                        <div className="empty-state">
                            <div
                                className="empty-scope"
                                aria-hidden="true" />
                            <p className="empty-title">No regulars found</p>
                            <p className="empty-hint">
                                No chatters attended at least {minStreams} stream{minStreams === 1 ? '' : 's'} for this creator.
                            </p>
                        </div>
                    )}

                    {!isLoading && !error && regulars.length > 0 && (
                        <div
                            role="region"
                            aria-label="Creator regulars"
                            aria-live="polite"
                        >
                            <Table
                                hover
                                responsive
                            >
                                <thead>
                                    <tr>
                                        <th scope="col">#</th>
                                        <th scope="col">Chatter</th>
                                        {SORTABLE_COLUMNS.map(column => (
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
                                    {regulars.map((regular, index) => (
                                        <tr key={regular.chatterId}>
                                            <td className="rank-num">{String(index + 1).padStart(2, '0')}</td>
                                            <td>{regular.nick}</td>
                                            <td style={{ minWidth: '140px' }}>
                                                <span className="mono">{regular.streamsAttended?.toLocaleString()}</span>
                                                <span
                                                    className="data-bar"
                                                    aria-hidden="true"
                                                >
                                                    <span
                                                        className="data-bar-fill"
                                                        style={{ width: `${Math.max(2, Math.round(((regular.streamsAttended || 0) / Math.max(1, totalStreams)) * 100))}%` }}
                                                    />
                                                </span>
                                            </td>
                                            <td className="mono text-end">
                                                {Math.round((regular.attendanceRate || 0) * 100)}%
                                            </td>
                                            <td className="text-end">
                                                {regular.lastSeen ? formatTimeAgo(regular.lastSeen) : '--'}
                                            </td>
                                            <td className="mono text-end">
                                                {regular.messageCount?.toLocaleString()}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </Table>
                        </div>
                    )}
                </Card.Body>
            </Card>
        </>
    )
}

export default RegularsPanel
