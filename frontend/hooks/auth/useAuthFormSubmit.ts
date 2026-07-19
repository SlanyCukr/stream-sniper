import { useState, type ChangeEvent, type FormEvent } from 'react'
import { toUiFailure, type UiFailure } from '@/utils/errorUtils'
import { useFormFieldChange } from './useFormFieldChange'

export interface UseAuthFormSubmitOptions<Form> {
    initialForm: Form
    validate: (form: Form) => string | null
    submit: (form: Form) => Promise<unknown>
    failureMessage: string
    onSuccess?: () => void
    externallyDisabled?: boolean
}

export const useAuthFormSubmit = <Form>({
    initialForm,
    validate,
    submit,
    failureMessage,
    onSuccess,
    externallyDisabled,
}: UseAuthFormSubmitOptions<Form>) => {
    const [formData, setFormData] = useState<Form>(initialForm)
    const [validationError, setValidationError] = useState('')
    const [failure, setFailure] = useState<UiFailure | null>(null)
    const [isSubmitting, setIsSubmitting] = useState(false)

    const updateField = useFormFieldChange(setFormData, setValidationError)
    const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
        updateField(event)
        setFailure(null)
    }

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
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
