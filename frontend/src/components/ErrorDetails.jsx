import {
    Card, Badge,
} from 'react-bootstrap'
import PropTypes from 'prop-types'

/**
 * Renders the detailed error information card
 */
const ErrorDetails = ({
    error, errorInfo,
}) => (
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
)

ErrorDetails.propTypes = {
    error: PropTypes.shape({
        response: PropTypes.shape({
            config: PropTypes.shape({
                url: PropTypes.string,
                method: PropTypes.string,
            }),
        }),
        stack: PropTypes.string,
    }).isRequired,
    errorInfo: PropTypes.shape({
        type: PropTypes.string,
        status: PropTypes.number,
        retryable: PropTypes.bool,
    }).isRequired,
}

export default ErrorDetails
