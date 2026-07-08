'use client'
import {
    Row, Col, Card, Table,
} from 'react-bootstrap'

/**
 * Components Health Table
 */
const ComponentsHealth = ({
    healthData, getStatusBadge,
}) => (
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
                            {Object.entries(healthData.components).map(([
                                component,
                                data,
                            ]) => (
                                <tr key={component}>
                                    <td className="text-capitalize">{component}</td>
                                    <td>{getStatusBadge(data.status)}</td>
                                    <td className="mono">
                                        {data.response_time_ms ? `${data.response_time_ms.toFixed(2)}ms` : 'N/A'}
                                    </td>
                                    <td>
                                        {data.details && (
                                            <small className="text-muted mono">
                                                {typeof data.details === 'object'
                                                    ? JSON.stringify(data.details, null, 2)
                                                    : data.details}
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
