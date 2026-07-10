'use client'
import { useMemo } from 'react'
import {
    Card, Table,
} from 'react-bootstrap'
import Link from 'next/link'
import { useChatterStreamActivity } from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatStreamTimestamp } from '@/utils/dateUtils'

/**
 * Footprint tab of the chatter explorer: every captured stream a chatter appears
 * in, with per-stream message counts and relative magnitude bars. Owns its own
 * query keyed on the selected chatter.
 *
 * @param {object} props
 * @param {{value: number, label: string}|null} props.chatter selected chatter option
 */
const ChatterFootprintPanel = ({ chatter }) => {
    const chatterId = chatter?.value || null

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

    const isLoading = Boolean(chatterId) && activityLoading

    return (
        <>
            {chatter && activity.length > 0 && !isLoading && (
                <div className="d-flex justify-content-end mb-2">
                    <span className="toolbar-readout">
                        <strong>{activity.length}</strong> streams · target <strong>{chatter.label}</strong>
                    </span>
                </div>
            )}

            <Card>
                <Card.Body className={!chatter || (chatterId && activity.length === 0 && !isLoading) ? 'p-0' : ''}>
                    {!chatter && (
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
                            aria-label="Chatter footprint results"
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

export default ChatterFootprintPanel
