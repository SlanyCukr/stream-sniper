'use client'
import type { ReactNode } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Container, Alert } from 'react-bootstrap'
import AuthenticatedGuard from '@/components/auth/guards/AuthenticatedGuard'

interface AdminGuardProps {
    children: ReactNode
}

const AdminGuard = ({ children }: AdminGuardProps) => {
    const {
        isAdmin,
    } = useAuth()

    return (
        <AuthenticatedGuard>
            {isAdmin ? children : (
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
            )}
        </AuthenticatedGuard>
    )
}

export default AdminGuard
