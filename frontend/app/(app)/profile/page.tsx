'use client'

import Profile from '@/views/auth/Profile'
import AuthenticatedGuard from '@/components/auth/guards/AuthenticatedGuard'

export default function ProfilePage() {
    return (
        <AuthenticatedGuard>
            <Profile />
        </AuthenticatedGuard>
    )
}
