'use client'

import type { ReactNode } from 'react'

interface WrappedSectionProps {
    label: string
    children: ReactNode
}

const WrappedSection = ({ label, children }: WrappedSectionProps) => (
    <section className="wrapped-section">
        <p className="section-label">{label}</p>
        {children}
    </section>
)

export default WrappedSection
