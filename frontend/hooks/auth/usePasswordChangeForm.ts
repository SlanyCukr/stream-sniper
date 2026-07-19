import { useState, type FormEvent } from 'react'
import { normalizeApiError } from '@/utils/errorUtils'
import { validatePasswordChange, type PasswordChangeData } from '@/utils/validationUtils'
import { useFormFieldChange } from './useFormFieldChange'

const INITIAL_PASSWORD_DATA: PasswordChangeData = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
}

export interface UsePasswordChangeFormOptions {
    onPasswordChange: (passwordData: PasswordChangeData) => Promise<unknown>
    onHide: () => void
}

export const usePasswordChangeForm = ({
    onPasswordChange, onHide,
}: UsePasswordChangeFormOptions) => {
    const [passwordData, setPasswordData] = useState<PasswordChangeData>(INITIAL_PASSWORD_DATA)
    const [error, setError] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)

    const reset = () => {
        setPasswordData(INITIAL_PASSWORD_DATA)
        setError('')
    }

    const handleChange = useFormFieldChange(setPasswordData, setError)

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        const validationError = validatePasswordChange(passwordData)
        if (validationError) {
            setError(validationError)
            return
        }

        setIsSubmitting(true)
        try {
            await onPasswordChange(passwordData)
            reset()
            onHide()
        } catch (changeError) {
            setError(normalizeApiError(changeError, 'Failed to change password').message)
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleClose = () => {
        if (isSubmitting) return
        reset()
        onHide()
    }

    return {
        passwordData,
        error,
        isSubmitting,
        handleChange,
        handleSubmit,
        handleClose,
    }
}
