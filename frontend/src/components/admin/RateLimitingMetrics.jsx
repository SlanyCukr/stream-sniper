import {
    Row, Col, Card, Table,
} from 'react-bootstrap'

/**
 * Rate Limiting Metrics Component
 */
const RateLimitingMetrics = ({ metricsData }) => (
    <Row className="mb-4">
        <Col>
            <Card>
                <Card.Header>
                    <h5 className="mb-0">Rate Limiting</h5>
                </Card.Header>
                <Card.Body>
                    <Table responsive>
                        <tbody>
                            <tr>
                                <td>Total Requests</td>
                                <td>{metricsData.rate_limiting.total_requests}</td>
                            </tr>
                            <tr>
                                <td>Rate Limited</td>
                                <td>{metricsData.rate_limiting.rate_limited_requests}</td>
                            </tr>
                            <tr>
                                <td>Rate Limit Percentage</td>
                                <td>
                                    {(metricsData.rate_limiting.rate_limit_percentage * 100).toFixed(2)}%
                                </td>
                            </tr>
                        </tbody>
                    </Table>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default RateLimitingMetrics
