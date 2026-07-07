'use client'
import {
    Row, Col, Card,
} from 'react-bootstrap'

/**
 * Processing Jobs Statistics Component
 */
const ProcessingJobsStatistics = ({ stats }) => (
    <Card>
        <Card.Header>
            <Card.Title>Processing Jobs Statistics</Card.Title>
        </Card.Header>
        <Card.Body>
            <Row>
                <Col md={2}>
                    <Card className="text-center bg-light">
                        <Card.Body>
                            <Card.Title className="text-primary">Total</Card.Title>
                            <Card.Text className="display-6">{stats.processing_jobs.total}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={2}>
                    <Card className="text-center bg-light">
                        <Card.Body>
                            <Card.Title className="text-secondary">Pending</Card.Title>
                            <Card.Text className="display-6">{stats.processing_jobs.pending || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={2}>
                    <Card className="text-center bg-light">
                        <Card.Body>
                            <Card.Title className="text-primary">In Progress</Card.Title>
                            <Card.Text className="display-6">{stats.processing_jobs.in_progress || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={2}>
                    <Card className="text-center bg-light">
                        <Card.Body>
                            <Card.Title className="text-success">Completed</Card.Title>
                            <Card.Text className="display-6">{stats.processing_jobs.completed || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={2}>
                    <Card className="text-center bg-light">
                        <Card.Body>
                            <Card.Title className="text-danger">Failed</Card.Title>
                            <Card.Text className="display-6">{stats.processing_jobs.failed || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={2}>
                    <Card className="text-center bg-light">
                        <Card.Body>
                            <Card.Title className="text-info">Recent 24h</Card.Title>
                            <Card.Text className="display-6">{stats.processing_jobs.recent_24h || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </Card.Body>
    </Card>
)

export default ProcessingJobsStatistics
