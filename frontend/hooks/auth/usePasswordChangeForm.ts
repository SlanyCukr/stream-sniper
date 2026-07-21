import { useState, type FormEvent } from 'react'
import { toUiFailure, type UiFailure } from '@/utils/errorUtils'
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
    const [validationError, setValidationError] = useState('')
    const [failure, setFailure] = useState<UiFailure | null>(null)
    const [isSubmitting, setIsSubmitting] = useState(false)

    const reset = () => {
        setPasswordData(INITIAL_PASSWORD_DATA)
        setValidationError('')
        setFailure(null)
    }

    const handleChange = useFormFieldChange(setPasswordData, (message) => {
        setValidationError(message)
        setFailure(null)
    })

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        const validationError = validatePasswordChange(passwordData)
        if (validationError) {
            setValidationError(validationError)
            return
        }

        setIsSubmitting(true)
        setValidationError('')
        setFailure(null)
        try {
            await onPasswordChange(passwordData)
            reset()
            onHide()
        } catch (changeError) {
            setFailure(toUiFailure(changeError, 'Failed to change password'))
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
        validationError,
        failure,
        isSubmitting,
        handleChange,
        handleSubmit,
        handleClose,
    }
}
