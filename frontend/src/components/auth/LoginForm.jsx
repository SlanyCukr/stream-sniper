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

const LoginForm = ({ onSwitchToRegister, onSuccess }) => {
    const [formData, setFormData] = useState({
        username: '',
        password: '',
    })
    const [localError, setLocalError] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    
    const { login, loading, error } = useAuth()

    const handleChange = (e) => {
        const { name, value } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: value
        }))
        // Clear errors when user starts typing
        if (localError) setLocalError('')
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setIsSubmitting(true)
        setLocalError('')

        // Client-side validation
        if (!formData.username.trim()) {
            setLocalError('Username is required')
            setIsSubmitting(false)
            return
        }

        if (!formData.password) {
            setLocalError('Password is required')
            setIsSubmitting(false)
            return
        }

        try {
            const result = await login(formData.username, formData.password)
            
            if (result.success) {
                // Clear form
                setFormData({
                    username: '',
                    password: '',
                })
                
                // Call success callback if provided
                if (onSuccess) {
                    onSuccess()
                }
            } else {
                setLocalError(result.error || 'Login failed')
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
                <h4 className="mb-0">Login</h4>
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
                            placeholder="Enter your username"
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
                            placeholder="Enter your password"
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
                                    Logging in...
                                </>
                            ) : (
                                'Login'
                            )}
                        </Button>
                        
                        {onSwitchToRegister && (
                            <Button
                                variant="link"
                                onClick={onSwitchToRegister}
                                disabled={isSubmitting || loading}
                                className="text-decoration-none"
                            >
                                Don't have an account? Register here
                            </Button>
                        )}
                    </div>
                </Form>
            </CardBody>
        </Card>
    )
}

export default LoginForm