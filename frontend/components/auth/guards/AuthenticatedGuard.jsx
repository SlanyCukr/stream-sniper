'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Container } from 'react-bootstrap'

import { useAuth } from '@/contexts/AuthContext'

export const AuthenticationLoadingState = () => (
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

const AuthenticatedGuard = ({ children }) => {
    const {
        isAuthenticated, isInitializing,
    } = useAuth()
    const router = useRouter()
    const pathname = usePathname()

    useEffect(() => {
        if (!isInitializing && !isAuthenticated) {
            router.replace(`/login?from=${encodeURIComponent(pathname)}`)
        }
    }, [
        isInitializing,
        isAuthenticated,
        router,
        pathname,
    ])

    if (isInitializing) return <AuthenticationLoadingState />
    if (!isAuthenticated) return null

    return children
}

export default AuthenticatedGuard
