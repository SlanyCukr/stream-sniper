'use client'
import {
    Row, Col, Card,
} from 'react-bootstrap'

/**
 * System Health Overview Cards
 */
const SystemHealthOverview = ({
    healthData, formatUptime, getStatusBadge,
}) => (
    <Row className="mb-4">
        <Col md={3}>
            <Card className="text-center">
                <Card.Body>
                    <Card.Title>System Status</Card.Title>
                    {getStatusBadge(healthData.status)}
                    <div className="mt-2">
                        <small className="text-muted">
                            Last updated: {new Date(healthData.timestamp).toLocaleString()}
                        </small>
                    </div>
                </Card.Body>
            </Card>
        </Col>
        <Col md={3}>
            <Card className="text-center">
                <Card.Body>
                    <Card.Title>Uptime</Card.Title>
                    <Card.Text className="h4">
                        {formatUptime(healthData.uptime_seconds)}
                    </Card.Text>
                </Card.Body>
            </Card>
        </Col>
        <Col md={3}>
            <Card className="text-center">
                <Card.Body>
                    <Card.Title>Version</Card.Title>
                    <Card.Text className="h4">{healthData.version}</Card.Text>
                </Card.Body>
            </Card>
        </Col>
        <Col md={3}>
            <Card className="text-center">
                <Card.Body>
                    <Card.Title>Memory Usage</Card.Title>
                    <Card.Text className="h4">
                        {healthData.system?.memory_usage_percent?.toFixed(1)}%
                    </Card.Text>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default SystemHealthOverview
