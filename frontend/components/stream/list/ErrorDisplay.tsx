'use client'
import React from 'react'
import ErrorAlert from '../../common/error/ErrorAlert'

interface ErrorDisplayProps {
    streamsError: unknown
    creatorsError: unknown
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
            {Boolean(streamsError) && (
                <ErrorAlert
                    error={streamsError}
                    title="Failed to load streams"
                    onRetry={onRetryStreams}
                    className="mb-2"
                />
            )}
            {Boolean(creatorsError) && (
                <ErrorAlert
                    error={creatorsError}
                    title="Failed to load creators"
                    onRetry={onRetryCreators}
                />
            )}
        </div>
    )
})

ErrorDisplay.displayName = 'ErrorDisplay'

export default ErrorDisplay
