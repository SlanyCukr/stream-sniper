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
            <Card className="mb-4">
                <Card.Header>
                    <h1 id="footprint-heading" className="page-title mb-0">Chatter footprint</h1>
                </Card.Header>
                <Card.Body>
                    <Form
                        onSubmit={handleSubmit}
                        className="d-flex gap-2"
                        role="search"
                    >
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
                        <Button
                            type="submit"
                            variant="primary"
                            disabled={!nickInput.trim()}
                        >
                            Search
                        </Button>
                    </Form>
                </Card.Body>
            </Card>

            <Card>
                <Card.Body>
                    {!submittedNick && (
                        <p className="mb-0">Enter a chatter nickname to see every stream they appear in.</p>
                    )}

                    {isLoading && (
                        <LoadingSpinner
                            size="lg"
                            text="Loading chatter footprint..."
                            card
                        />
                    )}

                    {isNotFound && !isLoading && (
                        <p className="mb-0">No chatter found with the nickname <strong>{submittedNick}</strong>.</p>
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
                                ? <p className="mb-0">This chatter has no recorded stream activity.</p>
                                : (
                                    <Table
                                        striped
                                        hover
                                        responsive
                                    >
                                        <thead>
                                            <tr>
                                                <th scope="col">Stream</th>
                                                <th scope="col">Streamer</th>
                                                <th scope="col">Started</th>
                                                <th scope="col">Messages</th>
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
                                                    <td>{formatStreamTimestamp(row[2])}</td>
                                                    <td>{row[5]?.toLocaleString()}</td>
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
