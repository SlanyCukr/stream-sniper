import React from 'react'
import {
    Card, Button, Alert,
} from 'react-bootstrap'
import PropTypes from 'prop-types'

/**
 * Error Boundary component to catch JavaScript errors anywhere in the child component tree
 * Logs those errors and displays a fallback UI instead of crashing the component tree
 */
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
        }
    }

    static getDerivedStateFromError(_error) {
        // Update state so the next render will show the fallback UI
        return {
            hasError: true,
        }
    }

    componentDidCatch(error, errorInfo) {
        // Log the error to console and any error reporting service
        console.error('ErrorBoundary caught an error:', error, errorInfo)

        this.setState({
            error,
            errorInfo,
        })

        // You can also log the error to an error reporting service here
        // Example: Sentry.captureException(error)
    }

    handleRetry = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null,
        })
    }

    render() {
        const {
            hasError, error, errorInfo,
        } = this.state
        const {
            children, fallback, showDetails,
        } = this.props

        if (hasError) {
            // Custom fallback UI provided
            if (fallback) {
                return fallback
            }

            // Default error UI
            return (
                <Card className="border-danger">
                    <Card.Header className="bg-danger text-white">
                        <h2 className="mb-0">⚠️ Something went wrong</h2>
                    </Card.Header>
                    <Card.Body>
                        <Alert variant="danger">
                            <Alert.Heading>Application Error</Alert.Heading>
                            <p>
                                We're sorry, but something unexpected happened.
                                Please try refreshing the page or contact support if the problem persists.
                            </p>
                        </Alert>

                        <div className="d-flex gap-2 mb-3">
                            <Button
                                variant="primary"
                                onClick={this.handleRetry}
                                aria-label="Try to recover from error"
                            >
                                Try Again
                            </Button>
                            <Button
                                variant="outline-secondary"
                                onClick={() => window.location.reload()}
                                aria-label="Reload the entire page"
                            >
                                Reload Page
                            </Button>
                        </div>

                        {showDetails && error && (
                            <details className="mt-3">
                                <summary className="btn btn-link p-0">
                                    Show technical details
                                </summary>
                                <pre className="mt-2 p-3 bg-light border rounded">
                                    <strong>Error:</strong> {error.toString()}
                                    {errorInfo && (
                                        <>
                                            <br />
                                            <strong>Component Stack:</strong>
                                            {errorInfo.componentStack}
                                        </>
                                    )}
                                </pre>
                            </details>
                        )}
                    </Card.Body>
                </Card>
            )
        }

        return children
    }
}

ErrorBoundary.propTypes = {
    children: PropTypes.node.isRequired,
    fallback: PropTypes.node,
    showDetails: PropTypes.bool,
}

ErrorBoundary.defaultProps = {
    fallback: null,
    showDetails: process.env.NODE_ENV === 'development',
}

export default ErrorBoundary
