'use client'
import {
    useCallback,
    useMemo,
    useState,
} from 'react'
import Link from 'next/link'
import { Card, Table } from 'react-bootstrap'
import { useSceneLeaderboard } from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

// Window toggle (days). Backend accepts only 7 or 30.
const WINDOW_TABS = [
    {
        key: 7,
        label: '7 days',
    },
    {
        key: 30,
        label: '30 days',
    },
]

// Sortable columns. `numeric` columns right-align and sink null values to the
// bottom in both sort directions; `nullable` marks the fields that may be null
// (unknown) per the nullable = unknown contract and render '--'.
const COLUMNS = [
    {
        key: 'rank',
        label: '#',
        align: 'start',
    },
    {
        key: 'name',
        label: 'Streamer',
        align: 'start',
    },
    {
        key: 'streams',
        label: 'Streams',
        align: 'end',
        numeric: true,
    },
    {
        key: 'hoursStreamed',
        label: 'Hours',
        align: 'end',
        numeric: true,
        nullable: true,
    },
    {
        key: 'totalMessages',
        label: 'Messages',
        align: 'end',
        numeric: true,
    },
    {
        key: 'msgsPerMin',
        label: 'Msgs/min',
        align: 'end',
        numeric: true,
        nullable: true,
    },
    {
        key: 'chatterAppearances',
        label: 'Chatter appearances',
        align: 'end',
        numeric: true,
    },
    {
        key: 'peakViewers',
        label: 'Peak viewers',
        align: 'end',
        numeric: true,
        nullable: true,
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

/** '--' for unknown (null) numbers; formatted otherwise. */
const numCell = (value, digits = 0) => {
    if (value == null) {
        return '--'
    }
    return digits > 0 ? value.toFixed(digits) : value.toLocaleString()
}

/**
 * Scene leaderboard: creators ranked by total messages over a 7- or 30-day
 * window, with a client-side sortable table. Rank comes from the backend
 * (total_messages DESC); nullable columns (hours, msgs/min, peak viewers)
 * render '--' and always sort to the bottom.
 */
const Scene = () => {
    const [
        windowDays,
        setWindowDays,
    ] = useState(7)
    const [
        sort,
        setSort,
    ] = useState('rank')
    const [
        dir,
        setDir,
    ] = useState('asc')

    const {
        data,
        isLoading,
        error,
        refetch,
    } = useSceneLeaderboard(windowDays)

    const entries = useMemo(() => data?.entries || [
    ], [
        data?.entries,
    ])

    const sortedEntries = useMemo(() => {
        const factor = dir === 'asc' ? 1 : -1
        const value = row => {
            if (sort === 'name') {
                return (row.displayName || row.nick || '').toLowerCase()
            }
            return row[sort]
        }
        return [
            ...entries,
        ].sort((r1, r2) => {
            const v1 = value(r1)
            const v2 = value(r2)
            // Unknown (null) numeric fields always sink to the bottom.
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
        entries,
        sort,
        dir,
    ])

    const handleSort = useCallback(key => {
        if (sort === key) {
            setDir(prev => (prev === 'asc' ? 'desc' : 'asc'))
        } else {
            setSort(key)
            // Names ascend; ranks ascend (1 first); every other metric descends.
            setDir(key === 'name' || key === 'rank' ? 'asc' : 'desc')
        }
    }, [
        sort,
    ])

    const handleWindowChange = useCallback(key => {
        setWindowDays(key)
    }, [
    ])

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Scene leaderboard</h1>
                    <p className="page-sub">Creators ranked by chat activity</p>
                </div>
            </div>

            <div
                className="toolbar scene-toolbar"
                role="search"
                aria-label="Leaderboard window">
                <div
                    className="chatter-tabs"
                    role="tablist"
                    aria-label="Window">
                    {WINDOW_TABS.map(tab => (
                        <button
                            key={tab.key}
                            type="button"
                            role="tab"
                            aria-selected={windowDays === tab.key}
                            className={windowDays === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                            onClick={() => handleWindowChange(tab.key)}>
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {error ? (
                <ErrorAlert
                    error={error}
                    title="Failed to load leaderboard"
                    onRetry={refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            ) : isLoading ? (
                <LoadingSpinner
                    text="Ranking the scene..."
                    centered
                />
            ) : entries.length === 0 ? (
                <div className="empty-state">
                    <span
                        className="empty-scope"
                        aria-hidden="true" />
                    <p className="empty-title">No streams in window</p>
                    <p className="empty-hint">
                        No captured streams fall inside the last {windowDays} days.
                    </p>
                </div>
            ) : (
                <Card>
                    <Card.Body className="p-0">
                        <div
                            role="region"
                            aria-label="Scene leaderboard">
                            <Table
                                hover
                                responsive
                                className="mb-0">
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
                                    {sortedEntries.map(entry => (
                                        <tr key={entry.creatorId}>
                                            <td className="rank-num">{String(entry.rank).padStart(2, '0')}</td>
                                            <td>
                                                <Link className="scene-streamer" href={`/creator/${entry.creatorId}`}>
                                                    {entry.profileImageUrl
                                                        ? (
                                                            <img
                                                                className="scene-avatar"
                                                                src={entry.profileImageUrl}
                                                                alt=""
                                                                width={28}
                                                                height={28}
                                                                loading="lazy"
                                                            />
                                                        )
                                                        : (
                                                            <span
                                                                className="scene-avatar scene-avatar-empty"
                                                                aria-hidden="true" />
                                                        )}
                                                    <span className="scene-streamer-name">
                                                        {entry.displayName || entry.nick}
                                                    </span>
                                                </Link>
                                            </td>
                                            <td className="mono text-end">{numCell(entry.streams)}</td>
                                            <td className="mono text-end">{numCell(entry.hoursStreamed, 1)}</td>
                                            <td className="mono text-end">{numCell(entry.totalMessages)}</td>
                                            <td className="mono text-end">{numCell(entry.msgsPerMin, 1)}</td>
                                            <td className="mono text-end">{numCell(entry.chatterAppearances)}</td>
                                            <td className="mono text-end">{numCell(entry.peakViewers)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </Table>
                        </div>
                    </Card.Body>
                </Card>
            )}
        </>
    )
}

export default Scene
