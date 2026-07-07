'use client'

import { useState } from 'react'
import {
    Modal, Form, Button, Alert, Spinner,
} from 'react-bootstrap'
import { validatePasswordChange } from '@/utils/validationUtils'

const PasswordChangeModal = ({
    show,
    onHide,
    onPasswordChange,
    loading,
}) => {
    const [
        passwordData,
        setPasswordData,
    ] = useState({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
    })
    const [
        passwordError,
        setPasswordError,
    ] = useState('')
    const [
        isSubmitting,
        setIsSubmitting,
    ] = useState(false)

    const handlePasswordInputChange = e => {
        const {
            name, value,
        } = e.target
        setPasswordData(prev => ({
            ...prev,
            [name]: value,
        }))
        // Clear error when user starts typing
        if (passwordError) {
            setPasswordError('')
        }
    }

    const handlePasswordSubmit = async e => {
        e.preventDefault()

        const validationError = validatePasswordChange(passwordData)
        if (validationError) {
            setPasswordError(validationError)
            return
        }

        setIsSubmitting(true)
        try {
            await onPasswordChange(passwordData)
            // Reset form on success
            setPasswordData({
                currentPassword: '',
                newPassword: '',
                confirmPassword: '',
            })
            setPasswordError('')
            onHide()
        } catch (error) {
            setPasswordError(error.message)
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleClose = () => {
        if (!isSubmitting) {
            setPasswordData({
                currentPassword: '',
                newPassword: '',
                confirmPassword: '',
            })
            setPasswordError('')
            onHide()
        }
    }

    return (
        <Modal
            show={show}
            onHide={handleClose}
            backdrop="static">
            <Modal.Header closeButton>
                <Modal.Title>Change Password</Modal.Title>
            </Modal.Header>
            <Form onSubmit={handlePasswordSubmit}>
                <Modal.Body>
                    {passwordError && (
                        <Alert
                            variant="danger"
                            className="mb-3">
                            {passwordError}
                        </Alert>
                    )}

                    <Form.Group className="mb-3">
                        <Form.Label htmlFor="currentPassword">Current Password</Form.Label>
                        <Form.Control
                            type="password"
                            id="currentPassword"
                            name="currentPassword"
                            value={passwordData.currentPassword}
                            onChange={handlePasswordInputChange}
                            placeholder="Enter your current password"
                            disabled={isSubmitting || loading}
                            required
                        />
                    </Form.Group>

                    <Form.Group className="mb-3">
                        <Form.Label htmlFor="newPassword">New Password</Form.Label>
                        <Form.Control
                            type="password"
                            id="newPassword"
                            name="newPassword"
                            value={passwordData.newPassword}
                            onChange={handlePasswordInputChange}
                            placeholder="Enter your new password"
                            disabled={isSubmitting || loading}
                            required
                        />
                        <Form.Text className="text-muted">
                            Password must be at least 8 characters long and contain both letters and numbers.
                        </Form.Text>
                    </Form.Group>

                    <Form.Group className="mb-3">
                        <Form.Label htmlFor="confirmPassword">Confirm New Password</Form.Label>
                        <Form.Control
                            type="password"
                            id="confirmPassword"
                            name="confirmPassword"
                            value={passwordData.confirmPassword}
                            onChange={handlePasswordInputChange}
                            placeholder="Confirm your new password"
                            disabled={isSubmitting || loading}
                            required
                        />
                    </Form.Group>
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        variant="secondary"
                        onClick={handleClose}
                        disabled={isSubmitting || loading}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="primary"
                        type="submit"
                        disabled={isSubmitting || loading}
                    >
                        {isSubmitting ? (
                            <>
                                <Spinner
                                    as="span"
                                    animation="border"
                                    size="sm"
                                    role="status"
                                    aria-hidden="true"
                                    className="me-2"
                                />
                                Changing Password...
                            </>
                        ) : (
                            'Change Password'
                        )}
                    </Button>
                </Modal.Footer>
            </Form>
        </Modal>
    )
}

export default PasswordChangeModal
