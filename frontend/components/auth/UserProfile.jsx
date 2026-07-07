'use client'

import { useState, useEffect } from 'react'
import {
    Card,
    Form,
    Alert,
    Spinner,
} from 'react-bootstrap'
import { useAuth } from '@/contexts/AuthContext'
import { validateEmail } from '@/utils/validationUtils'
import ProfileInfo from './ProfileInfo'
import ProfileActions from './ProfileActions'
import PasswordChangeModal from './PasswordChangeModal'

const UserProfile = () => {
    const {
        user, updateUser, changePassword, loading,
    } = useAuth()
    const [
        formData,
        setFormData,
    ] = useState({
        email: user?.email || '',
    })
    const [
        isEditing,
        setIsEditing,
    ] = useState(false)
    const [
        isSubmitting,
        setIsSubmitting,
    ] = useState(false)
    const [
        error,
        setError,
    ] = useState('')
    const [
        success,
        setSuccess,
    ] = useState('')
    const [
        showPasswordModal,
        setShowPasswordModal,
    ] = useState(false)

    // Update form data when user changes
    useEffect(() => {
        if (user) {
            setFormData({
                email: user.email || '',
            })
        }
    }, [
        user,
    ])

    const handleChange = e => {
        const {
            name, value,
        } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: value,
        }))
        // Clear error when user starts typing
        if (error) {
            setError('')
        }
    }

    const handleEditToggle = () => {
        if (isEditing) {
            // Cancel editing - reset form data
            setFormData({
                email: user?.email || '',
            })
            setError('')
        }
        setIsEditing(!isEditing)
    }

    const handleSubmit = async e => {
        e.preventDefault()

        // Validate email
        const emailError = validateEmail(formData.email)
        if (emailError) {
            setError(emailError)
            return
        }

        setIsSubmitting(true)
        setError('')

        try {
            const result = await updateUser({ email: formData.email })
            if (result.success) {
                setSuccess('Profile updated successfully!')
                setIsEditing(false)
                setTimeout(() => setSuccess(''), 5000)
            } else {
                setError(result.error || 'Failed to update profile')
            }
        } catch (updateError) {
            setError(updateError.message || 'Failed to update profile')
        } finally {
            setIsSubmitting(false)
        }
    }

    const handlePasswordChange = async passwordData => {
        const result = await changePassword(passwordData.currentPassword, passwordData.newPassword)

        if (!result.success) {
            throw new Error(result.error || 'Failed to change password')
        }

        setSuccess('Password changed successfully!')
        setTimeout(() => setSuccess(''), 5000)
    }

    if (loading) {
        return (
            <div
                className="d-flex justify-content-center align-items-center"
                style={{ minHeight: '300px' }}>
                <Spinner
                    animation="border"
                    variant="primary" />
            </div>
        )
    }

    return (
        <Card>
            <Card.Header>
                <h4>User Profile</h4>
            </Card.Header>
            <Card.Body>
                {error && (
                    <Alert
                        variant="danger"
                        className="mb-3">
                        {error}
                    </Alert>
                )}

                {success && (
                    <Alert
                        variant="success"
                        className="mb-3">
                        {success}
                    </Alert>
                )}

                <Form onSubmit={handleSubmit}>
                    <ProfileInfo
                        user={user}
                        formData={formData}
                        handleChange={handleChange}
                        isEditing={isEditing}
                        isSubmitting={isSubmitting}
                        loading={loading}
                    />

                    <div className="d-flex justify-content-end">
                        <ProfileActions
                            isEditing={isEditing}
                            isSubmitting={isSubmitting}
                            loading={loading}
                            handleEditToggle={handleEditToggle}
                            setShowPasswordModal={setShowPasswordModal}
                        />
                    </div>
                </Form>
            </Card.Body>

            <PasswordChangeModal
                show={showPasswordModal}
                onHide={() => setShowPasswordModal(false)}
                onPasswordChange={handlePasswordChange}
                loading={loading}
            />
        </Card>
    )
}

export default UserProfile
