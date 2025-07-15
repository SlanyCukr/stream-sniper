import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Alert, Spinner, Container } from 'react-bootstrap'
import { useAuth } from '../../contexts/AuthContext'

const ProtectedRoute = ({ 
    children, 
    requireAdmin = false, 
    fallback = null,
    redirectTo = '/login'
}) => {
    const { isAuthenticated, isAdmin, loading, user } = useAuth()
    const location = useLocation()

    // Show loading spinner while checking authentication
    if (loading) {
        return (
            <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '50vh' }}>
                <div className="text-center">
                    <Spinner animation="border" variant="primary" />
                    <p className="mt-2">Checking authentication...</p>
                </div>
            </Container>
        )
    }

    // Not authenticated
    if (!isAuthenticated) {
        if (fallback) {
            return fallback
        }
        
        // Redirect to login with current location
        return <Navigate to={redirectTo} state={{ from: location }} replace />
    }

    // Authenticated but need admin role
    if (requireAdmin && !isAdmin) {
        return (
            <Container className="mt-4">
                <Alert variant="danger">
                    <Alert.Heading>Access Denied</Alert.Heading>
                    <p>
                        You need administrator privileges to access this page.
                    </p>
                    <hr />
                    <p className="mb-0">
                        Current role: <strong>{user?.role}</strong>
                    </p>
                </Alert>
            </Container>
        )
    }

    // All checks passed, render the protected content
    return children
}

export default ProtectedRoute