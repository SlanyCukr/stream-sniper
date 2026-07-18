'use client'

import type { ReactNode } from 'react'

interface WrappedSectionProps {
    label: string
    children: ReactNode
}

/**
 * A single recap chapter: a `.section-label` heading over its content. Rendered
 * only by call sites that already decided the chapter has something to show, so
 * this component never owns the empty-skip decision itself.
 */
const WrappedSection = ({ label, children }: WrappedSectionProps) => (
    <section className="wrapped-section">
        <p className="section-label">{label}</p>
        {children}
    </section>
)

export default WrappedSection
