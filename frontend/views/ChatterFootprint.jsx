'use client'
import {
    useState, useCallback, useMemo,
} from 'react'
import {
    Card, Form, Button, Table,
} from 'react-bootstrap'
import Link from 'next/link'
import {
    useChatterId, useChatterStreamActivity,
} from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatStreamTimestamp } from '@/utils/dateUtils'

const ChatterFootprint = () => {
    const [
        nickInput,
        setNickInput,
    ] = useState('')
    const [
        submittedNick,
        setSubmittedNick,
    ] = useState('')

    const {
        data: chatterIdData,
        isLoading: chatterIdLoading,
        error: chatterIdError,
        refetch: refetchChatterId,
    } = useChatterId(submittedNick, Boolean(submittedNick))

    // The chatter_id endpoint returns a list of ints, e.g. [42]
    const chatterId = useMemo(() => {
        if (Array.isArray(chatterIdData)) return chatterIdData[0] || null
        return chatterIdData || null
    }, [
        chatterIdData,
    ])

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
     * Handles the nick lookup form submission
     * @param {object} event
     */
    const handleSubmit = useCallback(event => {
        event.preventDefault()
        setSubmittedNick(nickInput.trim())
    }, [
        nickInput,
    ])

    const isNotFound = chatterIdError?.response?.status === 404
    const isLoading = chatterIdLoading || activityLoading

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 id="footprint-heading" className="page-title">Chatter footprint</h1>
                    <p className="page-sub">Cross-stream presence trace</p>
                </div>
            </div>

            <Form
                onSubmit={handleSubmit}
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
                    <Form.Control
                        id="footprint-nick-input"
                        type="text"
                        value={nickInput}
                        onChange={event => setNickInput(event.target.value)}
                        placeholder="Enter chatter nickname..."
                        aria-label="Chatter nickname"
                    />
                </div>
                <Button
                    type="submit"
                    variant="primary"
                    disabled={!nickInput.trim()}
                >
                    <i
                        className="bi bi-crosshair me-2"
                        aria-hidden="true"></i>
                    Trace
                </Button>
                {submittedNick && activity.length > 0 && !isLoading && (
                    <span className="toolbar-readout">
                        <strong>{activity.length}</strong> streams · target <strong>{submittedNick}</strong>
                    </span>
                )}
            </Form>

            <Card>
                <Card.Body className={!submittedNick || isNotFound || (chatterId && activity.length === 0 && !isLoading) ? 'p-0' : ''}>
                    {!submittedNick && (
                        <div className="empty-state">
                            <div
                                className="empty-scope"
                                aria-hidden="true" />
                            <p className="empty-title">Awaiting target</p>
                            <p className="empty-hint">
                                Enter a chatter nickname to see every captured stream they appear in.
                            </p>
                        </div>
                    )}

                    {isLoading && (
                        <LoadingSpinner
                            size="lg"
                            text="Tracing chatter footprint..."
                        />
                    )}

                    {isNotFound && !isLoading && (
                        <div className="empty-state">
                            <div
                                className="empty-scope"
                                aria-hidden="true" />
                            <p className="empty-title">No signal</p>
                            <p className="empty-hint">
                                No chatter found with the nickname <strong>{submittedNick}</strong>.
                            </p>
                        </div>
                    )}

                    {chatterIdError && !isNotFound && !isLoading && (
                        <ErrorAlert
                            error={chatterIdError}
                            title="Failed to look up chatter"
                            onRetry={refetchChatterId}
                            showDetails={process.env.NODE_ENV === 'development'}
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
