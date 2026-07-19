'use client'
import type { ReactNode } from 'react'
import {
    Row, Col, Card, Table,
} from 'react-bootstrap'
import type { DetailedHealthComponent } from '@/hooks/admin/system/useSystemQueries'

interface ComponentsHealthProps {
    components: DetailedHealthComponent[]
    renderStatusBadge: (status: string) => ReactNode
}

const ComponentsHealth = ({
    components, renderStatusBadge,
}: ComponentsHealthProps) => (
    <Row className="mb-4">
        <Col>
            <Card>
                <Card.Body>
                    <h3 className="section-label mb-3">Components</h3>
                    <Table
                        hover
                        responsive>
                        <thead>
                            <tr>
                                <th>Component</th>
                                <th>Status</th>
                                <th>Response Time</th>
                                <th>Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            {components.map(component => (
                                <tr key={component.name}>
                                    <td className="text-capitalize">{component.name}</td>
                                    <td>{renderStatusBadge(component.status)}</td>
                                    <td className="mono">
                                        {component.responseTimeMs ? `${component.responseTimeMs.toFixed(2)}ms` : 'N/A'}
                                    </td>
                                    <td>
                                        {component.details && (
                                            <small className="text-muted mono">
                                                {typeof component.details === 'object'
                                                    ? JSON.stringify(component.details, null, 2)
                                                    : component.details}
                                            </small>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default ComponentsHealth
