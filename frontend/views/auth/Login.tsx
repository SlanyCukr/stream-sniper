'use client'

import {
    useState, useEffect,
} from 'react'
import {
    Alert,
} from 'react-bootstrap'
import {
    useRouter, useSearchParams,
} from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import Logo from '@/components/layout/Logo'
import LoginForm from '@/components/auth/login/LoginForm'
import RegisterForm from '@/components/auth/register/RegisterForm'

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

    // Get the intended destination from the query string, default to home.
    // Only accept same-origin paths — anything else (absolute URLs,
    // protocol-relative //host, javascript:) is an open-redirect/XSS vector.
    const rawFrom = searchParams.get('from')
    const from = rawFrom && rawFrom.startsWith('/') && !rawFrom.startsWith('//')
        ? rawFrom
        : '/'

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
        <div className="auth-screen">
            <div className="auth-panel">
                <div className="auth-brand">
                    <Logo />
                    <span className="auth-tagline">Twitch chat intelligence</span>
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
            </div>
        </div>
    )
}

export default Login
