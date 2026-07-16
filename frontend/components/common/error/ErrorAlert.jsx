'use client'
import React, {
    useState, useMemo,
} from 'react'
import {
    Alert, Badge, Button,
} from 'react-bootstrap'
import { normalizeApiError } from '@/utils/errorUtils'
import ErrorDetails from './ErrorDetails'

/** @typedef {Error & {response?:{config?:{url?:string, method?:string}}}} DetailedError */
/** @typedef {Omit<import('react-bootstrap').AlertProps, 'onClose'|'title'> & {error?:DetailedError|null, title?:string, onRetry?:(()=>unknown), onDismiss?:(()=>void), showDetails?:boolean}} ErrorAlertProps */

/** @param {ReturnType<typeof normalizeApiError>['type']} type */
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

/** @param {ReturnType<typeof normalizeApiError>['type']} type */
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


/** @param {ErrorAlertProps} props */
const ErrorAlert = ({
    error,
    title = 'Error',
    onRetry = undefined,
    onDismiss = undefined,
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
            ...normalizeApiError(error),
            timestamp: new Date().toLocaleString(),
        }
    }, [
        error,
    ])

    if (!errorInfo) {
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
                    <Alert.Heading className="h6 mb-2">
                        {title}
                        {errorInfo.status && (
                            <Badge
                                bg="secondary"
                                className="ms-2">
                                {errorInfo.status}
                            </Badge>
                        )}
                    </Alert.Heading>

                    <p className="mb-2">{errorInfo.message}</p>

                    <div className="d-flex gap-2 align-items-center">
                        {errorInfo.retryable && onRetry && (
                            <Button
                                size="sm"
                                variant={`outline-${alertVariant}`}
                                onClick={onRetry}
                                aria-label="Retry the failed operation">
                                🔄 Retry
                            </Button>
                        )}

                        {showDetails && (
                            <Button
                                size="sm"
                                variant="link"
                                className="p-0"
                                onClick={() => setDetailsVisible(visible => !visible)}
                                aria-expanded={detailsVisible}
                                aria-label={detailsVisible ? 'Hide error details' : 'Show error details'}>
                                {detailsVisible ? 'Hide Details' : 'Show Details'}
                            </Button>
                        )}

                        <small className="text-muted ms-auto">
                            {errorInfo.timestamp}
                        </small>
                    </div>

                    {detailsVisible && error && (
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
