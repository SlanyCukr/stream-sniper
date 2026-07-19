import type { ReactNode } from 'react'

interface EmptyStateProps {
    title: ReactNode
    children?: ReactNode
}

const EmptyState = ({
    title,
    children,
}: EmptyStateProps) => (
    <div className="empty-state">
        <div
            className="empty-scope"
            aria-hidden="true" />
        <p className="empty-title">{title}</p>
        <p className="empty-hint">{children}</p>
    </div>
)

export default EmptyState
