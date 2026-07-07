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
                <Card.Header>
                    <h5 className="mb-0">Components Health</h5>
                </Card.Header>
                <Card.Body>
                    <Table responsive>
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
                                    <td>
                                        {data.response_time_ms ? `${data.response_time_ms.toFixed(2)}ms` : 'N/A'}
                                    </td>
                                    <td>
                                        {data.details && (
                                            <small className="text-muted">
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
