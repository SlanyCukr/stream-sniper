'use client'
import React from 'react'
import ErrorAlert from '../ErrorAlert'

/**
 * Renders error display component for streams and creators
 * @param {object|null} streamsError
 * @param {object|null} creatorsError
 * @param {function} onRetryStreams
 * @param {function} onRetryCreators
 * @returns {JSX.Element|null}
 */
const ErrorDisplay = React.memo(({
    streamsError,
    creatorsError,
    onRetryStreams,
    onRetryCreators,
}) => {
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
