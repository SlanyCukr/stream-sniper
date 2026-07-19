'use client'
import React from 'react'
import ErrorAlert, { type DetailedError } from '../../common/error/ErrorAlert'

interface ErrorDisplayProps {
    streamsError: DetailedError | null
    creatorsError: DetailedError | null
    onRetryStreams: () => unknown
    onRetryCreators: () => unknown
}

/**
 * Renders error display component for streams and creators
 */
const ErrorDisplay = React.memo(({
    streamsError,
    creatorsError,
    onRetryStreams,
    onRetryCreators,
}: ErrorDisplayProps) => {
    if (!streamsError && !creatorsError) {
        return null
    }

    return (
        <div className="mb-3">
            {streamsError && (
                <ErrorAlert
                    error={streamsError}
                    title="Failed to load streams"
                    onRetry={onRetryStreams}
                    className="mb-2"
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            )}
            {creatorsError && (
                <ErrorAlert
                    error={creatorsError}
                    title="Failed to load creators"
                    onRetry={onRetryCreators}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            )}
        </div>
    )
})

ErrorDisplay.displayName = 'ErrorDisplay'

export default ErrorDisplay
