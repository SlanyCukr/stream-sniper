import { useState, type ChangeEvent, type FormEvent } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { toUiFailure, type UiFailure } from '@/utils/errorUtils'
import { validateEmail } from '@/utils/validationUtils'
import type { PasswordChangeData } from '@/utils/validationUtils'
import { useOwnedTimeout } from '@/hooks/useOwnedTimeout'

export const useUserProfile = () => {
    const {
        user, updateUser, changePassword, isInitializing,
    } = useAuth()
    const [emailDraft, setEmailDraft] = useState<string | null>(null)
    const [isEditing, setIsEditing] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [validationError, setValidationError] = useState('')
    const [failure, setFailure] = useState<UiFailure | null>(null)
    const [success, setSuccess] = useState('')
    const [showPasswordModal, setShowPasswordModal] = useState(false)
    const successTimeout = useOwnedTimeout()
    const formData = { email: emailDraft ?? user?.email ?? '' }

    const showSuccess = (message: string) => {
        setSuccess(message)
        successTimeout.schedule(() => setSuccess(''), 5000)
    }

    const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
        if (event.target.name === 'email') setEmailDraft(event.target.value)
        setValidationError('')
        setFailure(null)
    }

    const handleEditToggle = () => {
        if (isEditing) {
            setEmailDraft(null)
            setValidationError('')
            setFailure(null)
        }
        setIsEditing(previous => !previous)
    }

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        const emailError = validateEmail(formData.email)
        if (emailError) {
            setValidationError(emailError)
            return
        }

        setIsSubmitting(true)
        setValidationError('')
        setFailure(null)
        try {
            await updateUser({ email: formData.email })
            showSuccess('Profile updated successfully!')
            setIsEditing(false)
            setEmailDraft(null)
        } catch (updateError) {
            setFailure(toUiFailure(updateError, 'Failed to update profile'))
        } finally {
            setIsSubmitting(false)
        }
    }

    const handlePasswordChange = async (passwordData: PasswordChangeData) => {
        await changePassword(passwordData.currentPassword, passwordData.newPassword)
        showSuccess('Password changed successfully!')
    }

    return {
        user,
        isInitializing,
        formData,
        isEditing,
        isSubmitting,
        validationError,
        failure,
        success,
        showPasswordModal,
        handleChange,
        handleEditToggle,
        handleSubmit,
        handlePasswordChange,
        openPasswordModal: () => setShowPasswordModal(true),
        closePasswordModal: () => setShowPasswordModal(false),
    }
}
