import React, {
    useState, useMemo,
} from 'react'
import {
    Alert, Button, Card, Badge,
} from 'react-bootstrap'
import PropTypes from 'prop-types'
import {
    formatErrorMessage, getErrorType, isRetryableError,
} from '../utils/errorUtils'

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
        if (!error) return null

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

    const getVariantFromType = type => {
        switch (type) {
        case 'network':
            return 'warning'
        case 'authentication':
        case 'authorization':
            return 'warning'
        case 'not_found':
            return 'info'
        case 'server':
            return 'danger'
        case 'validation':
            return 'warning'
        default:
            return 'danger'
        }
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
                <span className="me-2 fs-4" role="img" aria-label={`${errorInfo.type} error`}>
                    {getErrorIcon(errorInfo.type)}
                </span>
                <div className="flex-grow-1">
                    <Alert.Heading className="h6 mb-2">
                        {title}
                        {errorInfo.status && (
                            <Badge bg="secondary" className="ms-2">
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
                                aria-label="Retry the failed operation"
                            >
                                🔄 Retry
                            </Button>
                        )}
                        
                        {showDetails && (
                            <Button
                                size="sm"
                                variant="link"
                                className="p-0"
                                onClick={() => setDetailsVisible(!detailsVisible)}
                                aria-expanded={detailsVisible}
                                aria-label={detailsVisible ? 'Hide error details' : 'Show error details'}
                            >
                                {detailsVisible ? 'Hide Details' : 'Show Details'}
                            </Button>
                        )}
                        
                        <small className="text-muted ms-auto">
                            {errorInfo.timestamp}
                        </small>
                    </div>
                    
                    {detailsVisible && (
                        <Card className="mt-3 border-secondary">
                            <Card.Header className="py-2">
                                <small className="text-muted">Technical Details</small>
                            </Card.Header>
                            <Card.Body className="py-2">
                                <dl className="row mb-0">
                                    <dt className="col-3">Error Type:</dt>
                                    <dd className="col-9">
                                        <Badge bg="secondary">{errorInfo.type}</Badge>
                                    </dd>
                                    
                                    {errorInfo.status && (
                                        <>
                                            <dt className="col-3">Status Code:</dt>
                                            <dd className="col-9">{errorInfo.status}</dd>
                                        </>
                                    )}
                                    
                                    {error.response?.config?.url && (
                                        <>
                                            <dt className="col-3">URL:</dt>
                                            <dd className="col-9">
                                                <code className="small">{error.response.config.url}</code>
                                            </dd>
                                        </>
                                    )}
                                    
                                    {error.response?.config?.method && (
                                        <>
                                            <dt className="col-3">Method:</dt>
                                            <dd className="col-9">
                                                <Badge bg="info">{error.response.config.method.toUpperCase()}</Badge>
                                            </dd>
                                        </>
                                    )}
                                    
                                    <dt className="col-3">Retryable:</dt>
                                    <dd className="col-9">
                                        <Badge bg={errorInfo.retryable ? 'success' : 'danger'}>
                                            {errorInfo.retryable ? 'Yes' : 'No'}
                                        </Badge>
                                    </dd>
                                </dl>
                                
                                {error.stack && (
                                    <details className="mt-2">
                                        <summary className="btn btn-link p-0 small">Stack Trace</summary>
                                        <pre className="mt-2 p-2 bg-light border rounded small">
                                            {error.stack}
                                        </pre>
                                    </details>
                                )}
                            </Card.Body>
                        </Card>
                    )}
                </div>
            </div>
        </Alert>
    )
}

ErrorAlert.propTypes = {
    error: PropTypes.object,
    title: PropTypes.string,
    onRetry: PropTypes.func,
    onDismiss: PropTypes.func,
    showDetails: PropTypes.bool,
    className: PropTypes.string,
    variant: PropTypes.oneOf([
        'primary',
        'secondary',
        'success',
        'danger',
        'warning',
        'info',
        'light',
        'dark',
    ]),
}

export default React.memo(ErrorAlert)