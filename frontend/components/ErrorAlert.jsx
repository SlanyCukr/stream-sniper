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
 * Helper function to get error icon class based on error type
 */
const getErrorIcon = type => {
    switch (type) {
        case 'network':
            return 'bi bi-wifi-off'
        case 'authentication':
        case 'authorization':
            return 'bi bi-shield-lock'
        case 'not_found':
            return 'bi bi-search'
        case 'server':
            return 'bi bi-x-octagon'
        case 'validation':
            return 'bi bi-exclamation-triangle'
        default:
            return 'bi bi-x-circle'
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
                <i
                    className={`${getErrorIcon(errorInfo.type)} me-3 fs-4`}
                    role="img"
                    aria-label={`${errorInfo.type} error`}
                ></i>
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
