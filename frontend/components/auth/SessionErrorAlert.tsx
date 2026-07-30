'use client'

import ErrorAlert from '@/components/common/error/ErrorAlert'
import { useAuth } from '@/contexts/AuthContext'

const SessionErrorAlert = () => {
    const { sessionError, dismissSessionError } = useAuth()
    if (!sessionError) return null

    return (
        <ErrorAlert
            error={sessionError.error}
            title="Session problem"
            onDismiss={dismissSessionError}
            showDetails={false}
        />
    )
}

export default SessionErrorAlert
