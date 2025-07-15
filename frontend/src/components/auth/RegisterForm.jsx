import React, { useState } from 'react'
import { 
    Card, 
    CardHeader, 
    CardBody, 
    Form, 
    FormGroup, 
    Label, 
    Input, 
    Button, 
    Alert, 
    Spinner 
} from 'react-bootstrap'
import { useAuth } from '../../contexts/AuthContext'

const RegisterForm = ({ onSwitchToLogin, onSuccess }) => {
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
    })
    const [localError, setLocalError] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    
    const { register, loading, error } = useAuth()

    const handleChange = (e) => {
        const { name, value } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: value
        }))
        // Clear errors when user starts typing
        if (localError) setLocalError('')
    }

    const validateForm = () => {
        if (!formData.username.trim()) {
            return 'Username is required'
        }

        if (formData.username.length < 3) {
            return 'Username must be at least 3 characters long'
        }

        if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
            return 'Username can only contain letters, numbers, hyphens, and underscores'
        }

        if (!formData.email.trim()) {
            return 'Email is required'
        }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
            return 'Please enter a valid email address'
        }

        if (!formData.password) {
            return 'Password is required'
        }

        if (formData.password.length < 8) {
            return 'Password must be at least 8 characters long'
        }

        if (!/[A-Za-z]/.test(formData.password)) {
            return 'Password must contain at least one letter'
        }

        if (!/[0-9]/.test(formData.password)) {
            return 'Password must contain at least one number'
        }

        if (formData.password !== formData.confirmPassword) {
            return 'Passwords do not match'
        }

        return null
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setIsSubmitting(true)
        setLocalError('')

        // Client-side validation
        const validationError = validateForm()
        if (validationError) {
            setLocalError(validationError)
            setIsSubmitting(false)
            return
        }

        try {
            const result = await register(formData.username, formData.email, formData.password)
            
            if (result.success) {
                // Clear form
                setFormData({
                    username: '',
                    email: '',
                    password: '',
                    confirmPassword: '',
                })
                
                // Call success callback if provided
                if (onSuccess) {
                    onSuccess()
                }
            } else {
                setLocalError(result.error || 'Registration failed')
            }
        } catch (error) {
            setLocalError('An unexpected error occurred')
        } finally {
            setIsSubmitting(false)
        }
    }

    const displayError = localError || error

    return (
        <Card className="shadow-sm">
            <CardHeader>
                <h4 className="mb-0">Register</h4>
            </CardHeader>
            <CardBody>
                {displayError && (
                    <Alert variant="danger" className="mb-3">
                        {displayError}
                    </Alert>
                )}
                
                <Form onSubmit={handleSubmit}>
                    <FormGroup className="mb-3">
                        <Label htmlFor="username">Username</Label>
                        <Input
                            type="text"
                            id="username"
                            name="username"
                            value={formData.username}
                            onChange={handleChange}
                            placeholder="Choose a username (3-50 characters)"
                            disabled={isSubmitting || loading}
                            required
                        />
                        <small className="text-muted">
                            Letters, numbers, hyphens, and underscores only
                        </small>
                    </FormGroup>

                    <FormGroup className="mb-3">
                        <Label htmlFor="email">Email</Label>
                        <Input
                            type="email"
                            id="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="Enter your email address"
                            disabled={isSubmitting || loading}
                            required
                        />
                    </FormGroup>

                    <FormGroup className="mb-3">
                        <Label htmlFor="password">Password</Label>
                        <Input
                            type="password"
                            id="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            placeholder="Choose a password (8+ characters)"
                            disabled={isSubmitting || loading}
                            required
                        />
                        <small className="text-muted">
                            Must contain at least one letter and one number
                        </small>
                    </FormGroup>

                    <FormGroup className="mb-3">
                        <Label htmlFor="confirmPassword">Confirm Password</Label>
                        <Input
                            type="password"
                            id="confirmPassword"
                            name="confirmPassword"
                            value={formData.confirmPassword}
                            onChange={handleChange}
                            placeholder="Confirm your password"
                            disabled={isSubmitting || loading}
                            required
                        />
                    </FormGroup>

                    <div className="d-grid gap-2">
                        <Button
                            variant="primary"
                            type="submit"
                            disabled={isSubmitting || loading}
                            size="lg"
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
                                    Creating account...
                                </>
                            ) : (
                                'Create Account'
                            )}
                        </Button>
                        
                        {onSwitchToLogin && (
                            <Button
                                variant="link"
                                onClick={onSwitchToLogin}
                                disabled={isSubmitting || loading}
                                className="text-decoration-none"
                            >
                                Already have an account? Login here
                            </Button>
                        )}
                    </div>
                </Form>
            </CardBody>
        </Card>
    )
}

export default RegisterForm