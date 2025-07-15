import {
    Alert, Badge,
} from 'react-bootstrap'
import PropTypes from 'prop-types'

/**
 * Renders the error header with title and status badge
 */
const ErrorHeader = ({
    title, errorInfo,
}) => (
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
)

ErrorHeader.propTypes = {
    title: PropTypes.string.isRequired,
    errorInfo: PropTypes.shape({
        status: PropTypes.number,
    }).isRequired,
}

export default ErrorHeader
