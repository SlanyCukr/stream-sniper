import { Alert } from 'react-bootstrap'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import type { useActionFeedback } from '@/hooks/admin/shared/useActionFeedback'

interface ActionFeedbackProps {
    feedback: ReturnType<typeof useActionFeedback>
}

const ActionFeedback = ({ feedback }: ActionFeedbackProps) => (
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
