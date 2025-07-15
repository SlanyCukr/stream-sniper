import {
    useState, useEffect,
} from 'react'
import {
    Container, Row, Col, Alert,
} from 'react-bootstrap'
import {
    useNavigate, useLocation,
} from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import LoginForm from '../../components/auth/LoginForm'
import RegisterForm from '../../components/auth/RegisterForm'

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
    const navigate = useNavigate()
    const location = useLocation()

    // Get the intended destination from location state, default to /starter
    const from = location.state?.from?.pathname || '/starter'

    useEffect(() => {
        // If already authenticated, redirect to intended destination
        if (isAuthenticated) {
            navigate(from, { replace: true })
        }
    }, [
        isAuthenticated,
        navigate,
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
            navigate(from, { replace: true })
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
