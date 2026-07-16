import { useState } from 'react'
import { toUiFailure } from '@/utils/errorUtils'
import { useFormFieldChange } from './useFormFieldChange'

/**
 * @template Form
 * @param {{
 *   initialForm: Form,
 *   validate: (form:Form) => string|null,
 *   submit: (form:Form) => Promise<unknown>,
 *   failureMessage: string,
 *   onSuccess?: () => void,
 *   externallyDisabled?: boolean,
 * }} options
 */
export const useAuthFormSubmit = ({
    initialForm,
    validate,
    submit,
    failureMessage,
    onSuccess,
    externallyDisabled,
}) => {
    const [formData, setFormData] = useState(initialForm)
    const [validationError, setValidationError] = useState('')
    const [failure, setFailure] = useState(
        /** @type {ReturnType<typeof toUiFailure>|null} */ (null),
    )
    const [isSubmitting, setIsSubmitting] = useState(false)

    const updateField = useFormFieldChange(setFormData, setValidationError)
    const handleChange = event => {
        updateField(event)
        setFailure(null)
    }

    const handleSubmit = async event => {
        event.preventDefault()
        const nextValidationError = validate(formData)
        if (nextValidationError) {
            setValidationError(nextValidationError)
            setFailure(null)
            return
        }

        setIsSubmitting(true)
        setValidationError('')
        setFailure(null)
        try {
            await submit(formData)
            setFormData(initialForm)
            onSuccess?.()
        } catch (submissionError) {
            setFailure(toUiFailure(submissionError, failureMessage))
        } finally {
            setIsSubmitting(false)
        }
    }

    return {
        formData,
        validationError,
        failure,
        errorMessage: validationError || failure?.normalized.message || '',
        isSubmitting,
        disabled: isSubmitting || externallyDisabled,
        handleChange,
        handleSubmit,
    }
}
