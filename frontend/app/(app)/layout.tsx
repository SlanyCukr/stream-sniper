'use client'

import FullLayout from '@/components/layout/FullLayout'

export default function AppLayout({ children }: { children: React.ReactNode }) {
    return <FullLayout>{children}</FullLayout>
}
