import { Card } from 'react-bootstrap'
import EmptyState from '@/components/common/EmptyState'

const CreatorPanelEmpty = ({
    title, children,
}) => (
    <Card>
        <Card.Body className="p-0">
            <EmptyState title={title}>{children}</EmptyState>
        </Card.Body>
    </Card>
)

export default CreatorPanelEmpty
