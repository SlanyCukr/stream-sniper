import { Alert } from 'react-bootstrap'
import ErrorAlert from '@/components/common/error/ErrorAlert'

const ActionFeedback = ({ feedback }) => (
    <>
        <ErrorAlert
            error={feedback.failure?.error}
            title={feedback.errorTitle}
            onDismiss={feedback.dismissError}
            className="mb-4" />

        {feedback.success && (
            <Alert
                variant="success"
                className="mb-4"
                dismissible
                closeLabel="Dismiss success message"
                onClose={feedback.dismissSuccess}>
                {feedback.success}
            </Alert>
        )}
    </>
)

export default ActionFeedback
