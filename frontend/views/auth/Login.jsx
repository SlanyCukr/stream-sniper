'use client'

import {
    useState, useEffect,
} from 'react'
import {
    Container, Row, Col, Alert,
} from 'react-bootstrap'
import {
    useRouter, useSearchParams,
} from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import LoginForm from '@/components/auth/LoginForm'
import RegisterForm from '@/components/auth/RegisterForm'

const Login = () => {
    const [
        showRegister,
        setShowRegister,
    ] = useState(false)
    const [
        successMessage,
        setSuccessMessage,
    ] = useState('')
    const { isAuthenticated } = useAuth()
    const router = useRouter()
    const searchParams = useSearchParams()

    // Get the intended destination from the query string, default to home
    const from = searchParams.get('from') || '/'

    useEffect(() => {
        // If already authenticated, redirect to intended destination
        if (isAuthenticated) {
            router.replace(from)
        }
    }, [
        isAuthenticated,
        router,
        from,
    ])

    const handleSwitchToRegister = () => {
        setShowRegister(true)
        setSuccessMessage('')
    }

    const handleSwitchToLogin = () => {
        setShowRegister(false)
        setSuccessMessage('')
    }

    const handleSuccess = () => {
        if (showRegister) {
            setSuccessMessage('Account created successfully! You are now logged in.')
        } else {
            setSuccessMessage('Login successful! Redirecting...')
        }

        // Redirect after a short delay to show success message
        setTimeout(() => {
            router.replace(from)
        }, 1500)
    }

    return (
        <Container className="mt-5">
            <Row className="justify-content-center">
                <Col
                    md={6}
                    lg={5}>
                    <div className="text-center mb-4">
                        <h2 className="text-primary">Stream Sniper</h2>
                        <p className="text-muted">
                            {showRegister ? 'Create your account' : 'Sign in to your account'}
                        </p>
                    </div>

                    {successMessage && (
                        <Alert
                            variant="success"
                            className="mb-3">
                            {successMessage}
                        </Alert>
                    )}

                    {showRegister ? (
                        <RegisterForm
                            onSwitchToLogin={handleSwitchToLogin}
                            onSuccess={handleSuccess}
                        />
                    ) : (
                        <LoginForm
                            onSwitchToRegister={handleSwitchToRegister}
                            onSuccess={handleSuccess}
                        />
                    )}
                </Col>
            </Row>
        </Container>
    )
}

export default Login
