'use client'

import { Suspense } from 'react'
import Login from '@/views/auth/Login'

export default function LoginPage() {
    // Login reads `?from=` via useSearchParams, which requires a Suspense
    // boundary in the App Router to avoid a full-route client-side bailout.
    return (
        <Suspense fallback={null}>
            <Login />
        </Suspense>
    )
}
