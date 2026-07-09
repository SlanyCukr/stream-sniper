'use client'
import {
    useState, useCallback, useMemo,
} from 'react'
import {
    Card, Table,
} from 'react-bootstrap'
import Link from 'next/link'
import {
    useChatterStreamActivity,
} from '@/hooks/useApiQuery'
import { retrieveChatterSearch } from '@/lib/api'
import AsyncSearchSelect from '@/components/AsyncSearchSelect'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatStreamTimestamp } from '@/utils/dateUtils'

const ChatterFootprint = () => {
    const [
        selectedChatter,
        setSelectedChatter,
    ] = useState(null)

    const chatterId = selectedChatter?.value || null

    const {
        data: activityData,
        isLoading: activityLoading,
        error: activityError,
        refetch: refetchActivity,
    } = useChatterStreamActivity(chatterId)

    const activity = useMemo(() => activityData || [
    ], [
        activityData,
    ])

    // Max message count across rows, for the relative magnitude bars
    const maxMessages = useMemo(() => Math.max(1, ...activity.map(row => row[5] || 0)), [
        activity,
    ])

    /**
     * Prefix-search chatter nicks for the autocomplete dropdown.
     * The backend returns [[id, nick], ...]; map to react-select options.
     * @param {string} query
     * @returns {Promise<Array<{value: number, label: string}>>}
     */
    const loadChatterOptions = useCallback(async query => {
        const trimmed = query.trim()
        if (trimmed.length < 2) {
            return []
        }
        try {
            const { data } = await retrieveChatterSearch(trimmed)
            return (data || []).map(([
                id,
                nick,
            ]) => ({
                value: id,
                label: nick,
            }))
        } catch {
            return []
        }
    }, [
    ])

    const noOptionsMessage = useCallback(({ inputValue }) => (
        inputValue && inputValue.trim().length >= 2
            ? `No chatters matching "${inputValue}"`
            : 'Type at least 2 characters to search'
    ), [
    ])

    const isLoading = Boolean(chatterId) && activityLoading

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 id="footprint-heading" className="page-title">Chatter footprint</h1>
                    <p className="page-sub">Cross-stream presence trace</p>
                </div>
            </div>

            <div
                className="toolbar"
                role="search"
            >
                <span
                    className="toolbar-label"
                    aria-hidden="true">
                    Trace
                </span>
                <div className="toolbar-field">
                    <label
                        htmlFor="footprint-nick-input"
                        className="visually-hidden"
                    >
                        Chatter nickname
                    </label>
                    <AsyncSearchSelect
                        instanceId="footprint-nick-select"
                        inputId="footprint-nick-input"
                        loadOptions={loadChatterOptions}
                        value={selectedChatter}
                        onChange={setSelectedChatter}
                        noOptionsMessage={noOptionsMessage}
                        placeholder="Search for a chatter..."
                        isClearable
                        aria-label="Chatter nickname"
                    />
                </div>
                {selectedChatter && activity.length > 0 && !isLoading && (
                    <span className="toolbar-readout">
                        <strong>{activity.length}</strong> streams · target <strong>{selectedChatter.label}</strong>
                    </span>
                )}
            </div>

            <Card>
                <Card.Body className={!selectedChatter || (chatterId && activity.length === 0 && !isLoading) ? 'p-0' : ''}>
                    {!selectedChatter && (
                        <div className="empty-state">
                            <div
                                className="empty-scope"
                                aria-hidden="true" />
                            <p className="empty-title">Awaiting target</p>
                            <p className="empty-hint">
                                Search for a chatter nickname to see every captured stream they appear in.
                            </p>
                        </div>
                    )}

                    {isLoading && (
                        <LoadingSpinner
                            size="lg"
                            text="Tracing chatter footprint..."
                        />
                    )}

                    {activityError && !isLoading && (
                        <ErrorAlert
                            error={activityError}
                            title="Failed to load chatter footprint"
                            onRetry={refetchActivity}
                            showDetails={process.env.NODE_ENV === 'development'}
                        />
                    )}

                    {chatterId && !isLoading && !activityError && (
                        <div
                            role="region"
                            aria-labelledby="footprint-heading"
                            aria-live="polite"
                        >
                            {activity.length === 0
                                ? (
                                    <div className="empty-state">
                                        <div
                                            className="empty-scope"
                                            aria-hidden="true" />
                                        <p className="empty-title">No activity</p>
                                        <p className="empty-hint">This chatter has no recorded stream activity.</p>
                                    </div>
                                )
                                : (
                                    <Table
                                        hover
                                        responsive
                                    >
                                        <thead>
                                            <tr>
                                                <th scope="col">Stream</th>
                                                <th scope="col">Streamer</th>
                                                <th scope="col">Started</th>
                                                <th
                                                    scope="col"
                                                    className="text-end">Messages</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {activity.map(row => (
                                                <tr key={row[0]}>
                                                    <td>
                                                        <Link href={`/stream/${row[0]}`}>
                                                            {row[1]}
                                                        </Link>
                                                    </td>
                                                    <td>{row[4]}</td>
                                                    <td className="mono small">{formatStreamTimestamp(row[2])}</td>
                                                    <td
                                                        className="mono text-end"
                                                        style={{ minWidth: '110px' }}>
                                                        {row[5]?.toLocaleString()}
                                                        <span
                                                            className="data-bar"
                                                            aria-hidden="true">
                                                            <span
                                                                className="data-bar-fill"
                                                                style={{ width: `${Math.max(2, Math.round(((row[5] || 0) / maxMessages) * 100))}%` }}
                                                            />
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </Table>
                                )}
                        </div>
                    )}
                </Card.Body>
            </Card>
        </>
    )
}

export default ChatterFootprint
