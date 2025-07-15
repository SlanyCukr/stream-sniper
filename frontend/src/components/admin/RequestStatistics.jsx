import {
    Row, Col, Card, Table, Button, ProgressBar,
} from 'react-bootstrap'

/**
 * Request and Cache Metrics Component
 */
const RequestStatistics = ({
    metricsData, flushCache,
}) => (
    <Row className="mb-4">
        <Col md={6}>
            <Card>
                <Card.Header>
                    <h5 className="mb-0">Request Statistics</h5>
                </Card.Header>
                <Card.Body>
                    <Table responsive>
                        <tbody>
                            <tr>
                                <td>Total Requests</td>
                                <td>{metricsData.requests.total_requests}</td>
                            </tr>
                            <tr>
                                <td>Successful Requests</td>
                                <td>{metricsData.requests.successful_requests}</td>
                            </tr>
                            <tr>
                                <td>Failed Requests</td>
                                <td>{metricsData.requests.failed_requests}</td>
                            </tr>
                            <tr>
                                <td>Average Response Time</td>
                                <td>{metricsData.requests.average_response_time_ms?.toFixed(2)}ms</td>
                            </tr>
                        </tbody>
                    </Table>
                </Card.Body>
            </Card>
        </Col>
        <Col md={6}>
            <Card>
                <Card.Header>
                    <h5 className="mb-0">Cache Performance</h5>
                </Card.Header>
                <Card.Body>
                    {metricsData.cache && (
                        <Table responsive>
                            <tbody>
                                <tr>
                                    <td>Hit Rate</td>
                                    <td>
                                        {(metricsData.cache.hit_rate * 100).toFixed(1)}%
                                        <ProgressBar
                                            now={metricsData.cache.hit_rate * 100}
                                            variant="success"
                                            className="mt-1"
                                        />
                                    </td>
                                </tr>
                                <tr>
                                    <td>Total Hits</td>
                                    <td>{metricsData.cache.total_hits}</td>
                                </tr>
                                <tr>
                                    <td>Total Misses</td>
                                    <td>{metricsData.cache.total_misses}</td>
                                </tr>
                                <tr>
                                    <td>Cache Operations</td>
                                    <td>{metricsData.cache.total_operations}</td>
                                </tr>
                            </tbody>
                        </Table>
                    )}
                    <div className="mt-3">
                        <Button
                            variant="outline-warning"
                            size="sm"
                            onClick={flushCache}
                        >
                            <i className="bi bi-arrow-clockwise me-1"></i>
                            Flush Cache
                        </Button>
                    </div>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default RequestStatistics
