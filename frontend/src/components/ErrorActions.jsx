import { Button } from 'react-bootstrap'
import PropTypes from 'prop-types'

/**
 * Renders the action buttons (retry and details toggle)
 */
const ErrorActions = ({
    errorInfo,
    onRetry,
    showDetails,
    detailsVisible,
    setDetailsVisible,
    alertVariant,
}) => (
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
)

ErrorActions.propTypes = {
    errorInfo: PropTypes.shape({
        retryable: PropTypes.bool,
        timestamp: PropTypes.string,
    }).isRequired,
    onRetry: PropTypes.func,
    showDetails: PropTypes.bool,
    detailsVisible: PropTypes.bool,
    setDetailsVisible: PropTypes.func,
    alertVariant: PropTypes.string,
}

export default ErrorActions
