'use client'
import { useState } from 'react'
import {
    Container, Row, Col, Card, Form, Button, Alert, Spinner,
} from 'react-bootstrap'
import { useRouter } from 'next/navigation'
import { getApiErrorMessage } from '@/lib/api'
import { useCreateAdminUser } from '@/hooks/useUserAdminQueries'

const CreateUser = () => {
    const router = useRouter()
    const [
        formData,
        setFormData,
    ] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
        role: 'user',
        is_active: true,
    })
    const [
        error,
        setError,
    ] = useState(null)
    const [
        success,
        setSuccess,
    ] = useState(null)
    const createUser = useCreateAdminUser()
    const loading = createUser.isPending

    const handleInputChange = e => {
        const {
            name, value, type, checked,
        } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value,
        }))
    }

    const validateForm = () => {
        const {
            username, email, password, confirmPassword,
        } = formData

        if (!username || !email || !password || !confirmPassword) {
            setError('All fields are required')
            return false
        }

        if (username.length < 3) {
            setError('Username must be at least 3 characters long')
            return false
        }

        if (password.length < 8) {
            setError('Password must be at least 8 characters long')
            return false
        }

        if (password !== confirmPassword) {
            setError('Passwords do not match')
            return false
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailRegex.test(email)) {
            setError('Please enter a valid email address')
            return false
        }

        const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$/
        if (!passwordRegex.test(password)) {
            setError('Password must contain at least one letter and one number')
            return false
        }

        return true
    }

    const handleSubmit = async e => {
        e.preventDefault()

        if (!validateForm()) {
            return
        }

        setError(null)
        setSuccess(null)

        try {
            const { data: userData } = await createUser.mutateAsync({
                username: formData.username,
                email: formData.email,
                password: formData.password,
                role: formData.role,
                is_active: formData.is_active,
            })

            setSuccess(`User "${userData.username}" created successfully!`)
            setFormData({
                username: '',
                email: '',
                password: '',
                confirmPassword: '',
                role: 'user',
                is_active: true,
            })

            // Redirect to user management after 2 seconds
            setTimeout(() => {
                router.push('/admin/users')
            }, 2000)
        } catch (createError) {
            console.error('Error creating user:', createError)
            setError(getApiErrorMessage(createError, 'Failed to create user'))
        }
    }

    return (
        <Container>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Create user</h1>
                    <p className="page-sub">Provision a new account</p>
                </div>
            </div>
            <Row>
                <Col
                    lg={8}
                    className="mx-auto">
                    <Card>
                        <Card.Body>
                            <h3 className="section-label mb-3">Account details</h3>
                            {error && (
                                <Alert
                                    variant="danger"
                                    dismissible
                                    onClose={() => setError(null)}>
                                    {error}
                                </Alert>
                            )}

                            {success && (
                                <Alert
                                    variant="success"
                                    dismissible
                                    onClose={() => setSuccess(null)}>
                                    {success}
                                </Alert>
                            )}

                            <Form onSubmit={handleSubmit}>
                                <Form.Group className="mb-3">
                                    <Form.Label>Username *</Form.Label>
                                    <Form.Control
                                        type="text"
                                        name="username"
                                        value={formData.username}
                                        onChange={handleInputChange}
                                        placeholder="Enter username"
                                        required
                                        minLength={3}
                                        maxLength={50}
                                    />
                                    <Form.Text className="text-muted">
                                        3-50 characters, letters, numbers, hyphens, and underscores only
                                    </Form.Text>
                                </Form.Group>

                                <Form.Group className="mb-3">
                                    <Form.Label>Email *</Form.Label>
                                    <Form.Control
                                        type="email"
                                        name="email"
                                        value={formData.email}
                                        onChange={handleInputChange}
                                        placeholder="Enter email address"
                                        required
                                    />
                                </Form.Group>

                                <Form.Group className="mb-3">
                                    <Form.Label>Password *</Form.Label>
                                    <Form.Control
                                        type="password"
                                        name="password"
                                        value={formData.password}
                                        onChange={handleInputChange}
                                        placeholder="Enter password"
                                        required
                                        minLength={8}
                                    />
                                    <Form.Text className="text-muted">
                                        At least 8 characters with letters and numbers
                                    </Form.Text>
                                </Form.Group>

                                <Form.Group className="mb-3">
                                    <Form.Label>Confirm Password *</Form.Label>
                                    <Form.Control
                                        type="password"
                                        name="confirmPassword"
                                        value={formData.confirmPassword}
                                        onChange={handleInputChange}
                                        placeholder="Confirm password"
                                        required
                                    />
                                </Form.Group>

                                <Form.Group className="mb-3">
                                    <Form.Label>Role</Form.Label>
                                    <Form.Select
                                        name="role"
                                        value={formData.role}
                                        onChange={handleInputChange}
                                    >
                                        <option value="user">User</option>
                                        <option value="admin">Admin</option>
                                    </Form.Select>
                                </Form.Group>

                                <Form.Group className="mb-3">
                                    <Form.Check
                                        type="checkbox"
                                        name="is_active"
                                        checked={formData.is_active}
                                        onChange={handleInputChange}
                                        label="Active User"
                                    />
                                    <Form.Text className="text-muted">
                                        Inactive users cannot log in
                                    </Form.Text>
                                </Form.Group>

                                <div className="d-grid gap-2">
                                    <Button
                                        variant="primary"
                                        type="submit"
                                        disabled={loading}
                                    >
                                        {loading ? (
                                            <>
                                                <Spinner
                                                    animation="border"
                                                    size="sm"
                                                    className="me-2" />
                                                Creating User...
                                            </>
                                        ) : (
                                            <>
                                                <i
                                                    className="bi bi-person-plus me-2"
                                                    aria-hidden="true" />
                                                Create user
                                            </>
                                        )}
                                    </Button>
                                    <Button
                                        variant="outline-primary"
                                        onClick={() => router.push('/admin/users')}
                                        disabled={loading}
                                    >
                                        Cancel
                                    </Button>
                                </div>
                            </Form>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </Container>
    )
}

export default CreateUser
