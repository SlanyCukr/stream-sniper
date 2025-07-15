import React, { useState } from 'react'
import { 
    Card, 
    Form, 
    Button, 
    Alert, 
    Spinner,
    Row,
    Col,
    Badge,
    Modal
} from 'react-bootstrap'
import { useAuth } from '../../contexts/AuthContext'

const UserProfile = () => {
    const { user, updateUser, changePassword, loading, error } = useAuth()
    const [isEditing, setIsEditing] = useState(false)
    const [showPasswordModal, setShowPasswordModal] = useState(false)
    const [formData, setFormData] = useState({
        email: user?.email || '',
    })
    const [passwordData, setPasswordData] = useState({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
    })
    const [localError, setLocalError] = useState('')
    const [localSuccess, setLocalSuccess] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)

    const handleChange = (e) => {
        const { name, value } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: value
        }))
        if (localError) setLocalError('')
    }

    const handlePasswordChange = (e) => {
        const { name, value } = e.target
        setPasswordData(prev => ({
            ...prev,
            [name]: value
        }))
        if (localError) setLocalError('')
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setIsSubmitting(true)
        setLocalError('')
        setLocalSuccess('')

        // Client-side validation
        if (!formData.email.trim()) {
            setLocalError('Email is required')
            setIsSubmitting(false)
            return
        }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
            setLocalError('Please enter a valid email address')
            setIsSubmitting(false)
            return
        }

        try {
            const result = await updateUser({ email: formData.email })
            
            if (result.success) {
                setLocalSuccess('Profile updated successfully')
                setIsEditing(false)
            } else {
                setLocalError(result.error || 'Update failed')
            }
        } catch (error) {
            setLocalError('An unexpected error occurred')
        } finally {
            setIsSubmitting(false)
        }
    }

    const handlePasswordSubmit = async (e) => {
        e.preventDefault()
        setIsSubmitting(true)
        setLocalError('')
        setLocalSuccess('')

        // Client-side validation
        if (!passwordData.currentPassword) {
            setLocalError('Current password is required')
            setIsSubmitting(false)
            return
        }

        if (!passwordData.newPassword) {
            setLocalError('New password is required')
            setIsSubmitting(false)
            return
        }

        if (passwordData.newPassword.length < 8) {
            setLocalError('New password must be at least 8 characters long')
            setIsSubmitting(false)
            return
        }

        if (!/[A-Za-z]/.test(passwordData.newPassword)) {
            setLocalError('New password must contain at least one letter')
            setIsSubmitting(false)
            return
        }

        if (!/[0-9]/.test(passwordData.newPassword)) {
            setLocalError('New password must contain at least one number')
            setIsSubmitting(false)
            return
        }

        if (passwordData.newPassword !== passwordData.confirmPassword) {
            setLocalError('New passwords do not match')
            setIsSubmitting(false)
            return
        }

        try {
            const result = await changePassword(passwordData.currentPassword, passwordData.newPassword)
            
            if (result.success) {
                setLocalSuccess('Password changed successfully')
                setShowPasswordModal(false)
                setPasswordData({
                    currentPassword: '',
                    newPassword: '',
                    confirmPassword: '',
                })
            } else {
                setLocalError(result.error || 'Password change failed')
            }
        } catch (error) {
            setLocalError('An unexpected error occurred')
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleEditToggle = () => {
        if (isEditing) {
            // Reset form data when canceling edit
            setFormData({
                email: user?.email || '',
            })
            setLocalError('')
            setLocalSuccess('')
        }
        setIsEditing(!isEditing)
    }

    const displayError = localError || error

    return (
        <div>
            <Card className="shadow-sm">
                <Card.Header>
                    <h4 className="mb-0">User Profile</h4>
                </Card.Header>
                <Card.Body>
                    {displayError && (
                        <Alert variant="danger" className="mb-3">
                            {displayError}
                        </Alert>
                    )}
                    
                    {localSuccess && (
                        <Alert variant="success" className="mb-3">
                            {localSuccess}
                        </Alert>
                    )}
                    
                    <Form onSubmit={handleSubmit}>
                        <Row>
                            <Col md={6}>
                                <Form.Group className="mb-3">
                                    <Form.Label>Username</Form.Label>
                                    <Form.Control
                                        type="text"
                                        value={user?.username || ''}
                                        disabled
                                        className="bg-light"
                                    />
                                    <small className="text-muted">Username cannot be changed</small>
                                </Form.Group>
                            </Col>
                            <Col md={6}>
                                <Form.Group className="mb-3">
                                    <Form.Label>Role</Form.Label>
                                    <div>
                                        <Badge 
                                            variant={user?.role === 'admin' ? 'danger' : 'primary'}
                                            className="fs-6"
                                        >
                                            {user?.role || 'user'}
                                        </Badge>
                                    </div>
                                </Form.Group>
                            </Col>
                        </Row>

                        <Form.Group className="mb-3">
                            <Form.Label htmlFor="email">Email</Form.Label>
                            <Form.Control
                                type="email"
                                id="email"
                                name="email"
                                value={formData.email}
                                onChange={handleChange}
                                placeholder="Enter your email address"
                                disabled={!isEditing || isSubmitting || loading}
                                required
                            />
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label>Account Status</Form.Label>
                            <div>
                                <Badge variant={user?.is_active ? 'success' : 'warning'}>
                                    {user?.is_active ? 'Active' : 'Inactive'}
                                </Badge>
                            </div>
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label>Member Since</Form.Label>
                            <div className="text-muted">
                                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                            </div>
                        </Form.Group>

                        <div className="d-flex gap-2">
                            {isEditing ? (
                                <>
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
                                                Saving...
                                            </>
                                        ) : (
                                            'Save Changes'
                                        )}
                                    </Button>
                                    <Button
                                        variant="secondary"
                                        onClick={handleEditToggle}
                                        disabled={isSubmitting || loading}
                                    >
                                        Cancel
                                    </Button>
                                </>
                            ) : (
                                <>
                                    <Button
                                        variant="primary"
                                        onClick={handleEditToggle}
                                        disabled={loading}
                                    >
                                        Edit Profile
                                    </Button>
                                    <Button
                                        variant="outline-primary"
                                        onClick={() => setShowPasswordModal(true)}
                                        disabled={loading}
                                    >
                                        Change Password
                                    </Button>
                                </>
                            )}
                        </div>
                    </Form>
                </Card.Body>
            </Card>

            {/* Password Change Modal */}
            <Modal show={showPasswordModal} onHide={() => setShowPasswordModal(false)}>
                <Modal.Header closeButton>
                    <Modal.Title>Change Password</Modal.Title>
                </Modal.Header>
                <Form onSubmit={handlePasswordSubmit}>
                    <Modal.Body>
                        {displayError && (
                            <Alert variant="danger" className="mb-3">
                                {displayError}
                            </Alert>
                        )}
                        
                        <Form.Group className="mb-3">
                            <Form.Label htmlFor="currentPassword">Current Password</Form.Label>
                            <Form.Control
                                type="password"
                                id="currentPassword"
                                name="currentPassword"
                                value={passwordData.currentPassword}
                                onChange={handlePasswordChange}
                                placeholder="Enter your current password"
                                disabled={isSubmitting}
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
                                onChange={handlePasswordChange}
                                placeholder="Enter new password (8+ characters)"
                                disabled={isSubmitting}
                                required
                            />
                            <small className="text-muted">
                                Must contain at least one letter and one number
                            </small>
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label htmlFor="confirmPassword">Confirm New Password</Form.Label>
                            <Form.Control
                                type="password"
                                id="confirmPassword"
                                name="confirmPassword"
                                value={passwordData.confirmPassword}
                                onChange={handlePasswordChange}
                                placeholder="Confirm new password"
                                disabled={isSubmitting}
                                required
                            />
                        </Form.Group>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button
                            variant="secondary"
                            onClick={() => setShowPasswordModal(false)}
                            disabled={isSubmitting}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="primary"
                            type="submit"
                            disabled={isSubmitting}
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
                                    Changing...
                                </>
                            ) : (
                                'Change Password'
                            )}
                        </Button>
                    </Modal.Footer>
                </Form>
            </Modal>
        </div>
    )
}

export default UserProfile