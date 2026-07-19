import { Alert } from 'react-bootstrap'
import ErrorAlert, { type DetailedError } from '@/components/common/error/ErrorAlert'
import type { useActionFeedback } from '@/hooks/admin/shared/useActionFeedback'

interface ActionFeedbackProps {
    feedback: ReturnType<typeof useActionFeedback>
}

const ActionFeedback = ({ feedback }: ActionFeedbackProps) => (
    <>
        <ErrorAlert
            // toUiFailure keeps the raw thrown value as `unknown`; ErrorAlert only reads Error-shaped fields off it
            error={feedback.failure?.error as DetailedError | null | undefined}
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
