import { useState, type ChangeEvent, type FormEvent } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { normalizeApiError } from '@/utils/errorUtils'
import { validateEmail } from '@/utils/validationUtils'
import type { PasswordChangeData } from '@/utils/validationUtils'

export const useUserProfile = () => {
    const {
        user, updateUser, changePassword, isInitializing,
    } = useAuth()
    const [emailDraft, setEmailDraft] = useState<string | null>(null)
    const [isEditing, setIsEditing] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')
    const [showPasswordModal, setShowPasswordModal] = useState(false)
    const formData = { email: emailDraft ?? user?.email ?? '' }

    const showSuccess = (message: string) => {
        setSuccess(message)
        setTimeout(() => setSuccess(''), 5000)
    }

    const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
        if (event.target.name === 'email') setEmailDraft(event.target.value)
        setError('')
    }

    const handleEditToggle = () => {
        if (isEditing) {
            setEmailDraft(null)
            setError('')
        }
        setIsEditing(previous => !previous)
    }

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        const emailError = validateEmail(formData.email)
        if (emailError) {
            setError(emailError)
            return
        }

        setIsSubmitting(true)
        setError('')
        try {
            await updateUser({ email: formData.email })
            showSuccess('Profile updated successfully!')
            setIsEditing(false)
            setEmailDraft(null)
        } catch (updateError) {
            setError(normalizeApiError(updateError, 'Failed to update profile').message)
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
        error,
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
