'use client'
import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import {
    Container, Alert,
} from 'react-bootstrap'

const AdminGuard = ({ children }) => {
    const {
        isAuthenticated, isAdmin, loading,
    } = useAuth()
    const router = useRouter()
    const pathname = usePathname()

    useEffect(() => {
        if (!loading && !isAuthenticated) {
            router.replace(`/login?from=${encodeURIComponent(pathname)}`)
        }
    }, [
        loading,
        isAuthenticated,
        router,
        pathname,
    ])

    // Show loading state while checking authentication
    if (loading) {
        return (
            <Container
                className="d-flex justify-content-center align-items-center"
                style={{ minHeight: '300px' }}>
                <div
                    className="spinner-border text-primary"
                    role="status">
                    <span className="visually-hidden">Loading...</span>
                </div>
            </Container>
        )
    }

    // Render nothing while redirecting unauthenticated users to login
    if (!isAuthenticated) {
        return null
    }

    // Show access denied if authenticated but not admin
    if (!isAdmin) {
        return (
            <Container className="mt-5">
                <Alert variant="danger">
                    <Alert.Heading>Access Denied</Alert.Heading>
                    <p>
                        You do not have permission to access this page.
                        This area is restricted to administrators only.
                    </p>
                    <hr />
                    <p className="mb-0">
                        If you believe this is an error, please contact your system administrator.
                    </p>
                </Alert>
            </Container>
        )
    }

    // Render the protected content
    return children
}

export default AdminGuard
