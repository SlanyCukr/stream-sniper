'use client'
import {
    useMemo,
} from 'react'
import {
    Card,
} from 'react-bootstrap'
import { useStreams } from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

const UserMessages = () => {
    // Use TanStack Query hook for fetching streams
    const {
        data: streamsData,
        isLoading,
        error,
        refetch,
    } = useStreams(-1, 0) // Get all streams from first page

    // Memoize streams data extraction
    const streams = useMemo(() => streamsData?.streams || [
    ], [
        streamsData?.streams,
    ])

    if (isLoading) {
        return (
            <LoadingSpinner
                size="lg"
                text="Loading user messages..."
                card
            />
        )
    }

    if (error) {
        return (
            <ErrorAlert
                error={error}
                title="Failed to load streams"
                onRetry={refetch}
                showDetails={process.env.NODE_ENV === 'development'}
            />
        )
    }

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 id="chatter-messages-heading" className="page-title">Chatter messages</h1>
                    <p className="page-sub">Cross-stream message analysis</p>
                </div>
            </div>

            <Card>
                <Card.Body className="p-0">
                    <div
                        className="empty-state"
                        role="status"
                        aria-live="polite"
                        aria-labelledby="chatter-messages-heading"
                    >
                        <div
                            className="empty-scope"
                            aria-hidden="true" />
                        <p className="empty-title">Module under construction</p>
                        <p className="empty-hint">
                            Chatter message analysis is not wired up yet.
                            {' '}{streams.length.toLocaleString()} streams are already captured and waiting —
                            in the meantime, open a stream and use its chat replay.
                        </p>
                    </div>
                </Card.Body>
            </Card>
        </>
    )
}

export default UserMessages
