import {
    useMemo,
} from 'react'
import {
    Card,
} from 'react-bootstrap'
import { useStreams } from '../../hooks/useApiQuery'
import LoadingSpinner from '../../components/LoadingSpinner'
import ErrorAlert from '../../components/ErrorAlert'

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

    // Memoize streams count calculation
    const streamsCount = useMemo(() => streams.length, [
        streams.length,
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
        <Card>
            <Card.Header>
                <h1 id="chatter-messages-heading">Chatter messages</h1>
            </Card.Header>
            <Card.Body>
                <div
                    role="status"
                    aria-live="polite"
                    aria-labelledby="chatter-messages-heading"
                >
                    <p>Found <strong>{streamsCount}</strong> streams</p>
                    <p>TODO: Implement chatter message analysis functionality</p>
                </div>
            </Card.Body>
        </Card>
    )
}

export default UserMessages
