'use client'
import React, {
    useState, useMemo,
} from 'react'
import {
    Alert,
} from 'react-bootstrap'
import {
    formatErrorMessage, getErrorType, isRetryableError,
} from '@/utils/errorUtils'
import ErrorHeader from './ErrorHeader'
import ErrorActions from './ErrorActions'
import ErrorDetails from './ErrorDetails'

/**
 * Helper function to get error icon based on error type
 */
const getErrorIcon = type => {
    switch (type) {
        case 'network':
            return '🌐'
        case 'authentication':
        case 'authorization':
            return '🔐'
        case 'not_found':
            return '🔍'
        case 'server':
            return '🚫'
        case 'validation':
            return '⚠️'
        default:
            return '❌'
    }
}

/**
 * Helper function to get alert variant based on error type
 */
const getVariantFromType = type => {
    switch (type) {
        case 'network':
        case 'authentication':
        case 'authorization':
        case 'validation':
            return 'warning'
        case 'not_found':
            return 'info'
        case 'server':
        default:
            return 'danger'
    }
}


/**
 * Enhanced error display component with retry functionality and better UX
 */
const ErrorAlert = ({
    error,
    title = 'Error',
    onRetry,
    onDismiss,
    showDetails = false,
    className = '',
    variant = 'danger',
    ...props
}) => {
    const [
        detailsVisible,
        setDetailsVisible,
    ] = useState(false)

    const errorInfo = useMemo(() => {
        if (!error) {
            return null
        }

        return {
            message: formatErrorMessage(error),
            type: getErrorType(error),
            retryable: isRetryableError(error),
            status: error.response?.status,
            timestamp: new Date().toLocaleString(),
        }
    }, [
        error,
    ])

    if (!error || !errorInfo) {
        return null
    }

    const alertVariant = variant === 'danger' ? getVariantFromType(errorInfo.type) : variant

    return (
        <Alert
            variant={alertVariant}
            dismissible={Boolean(onDismiss)}
            onClose={onDismiss}
            className={className}
            {...props}
        >
            <div className="d-flex align-items-start">
                <span
                    className="me-2 fs-4"
                    role="img"
                    aria-label={`${errorInfo.type} error`}
                >
                    {getErrorIcon(errorInfo.type)}
                </span>
                <div className="flex-grow-1">
                    <ErrorHeader
                        title={title}
                        errorInfo={errorInfo} />

                    <p className="mb-2">{errorInfo.message}</p>

                    <ErrorActions
                        errorInfo={errorInfo}
                        onRetry={onRetry}
                        showDetails={showDetails}
                        detailsVisible={detailsVisible}
                        setDetailsVisible={setDetailsVisible}
                        alertVariant={alertVariant}
                    />

                    {detailsVisible && (
                        <ErrorDetails
                            error={error}
                            errorInfo={errorInfo} />
                    )}
                </div>
            </div>
        </Alert>
    )
}

export default React.memo(ErrorAlert)
