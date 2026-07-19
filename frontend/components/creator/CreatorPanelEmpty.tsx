import type { ReactNode } from 'react'
import { Card } from 'react-bootstrap'
import EmptyState from '@/components/common/EmptyState'

interface CreatorPanelEmptyProps {
    title: string
    children?: ReactNode
}

const CreatorPanelEmpty = ({
    title, children,
}: CreatorPanelEmptyProps) => (
    <Card>
        <Card.Body className="p-0">
            <EmptyState title={title}>{children}</EmptyState>
        </Card.Body>
    </Card>
)

export default CreatorPanelEmpty
