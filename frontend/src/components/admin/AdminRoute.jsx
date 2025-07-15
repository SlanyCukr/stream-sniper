import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Container, Alert } from 'react-bootstrap';

const AdminRoute = ({ children }) => {
    const { isAuthenticated, isAdmin, loading } = useAuth();

    // Show loading state while checking authentication
    if (loading) {
        return (
            <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '300px' }}>
                <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                </div>
            </Container>
        );
    }

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    // Show access denied if not admin
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
        );
    }

    // Render the protected component
    return children;
};

export default AdminRoute;