'use client'
import {
    Row, Col, Card,
} from 'react-bootstrap'

/**
 * Rate Limiting Metrics Component
 */
const RateLimitingMetrics = ({ metricsData }) => (
    <Row className="mb-4">
        <Col>
            <Card>
                <Card.Body>
                    <h3 className="section-label mb-3">Rate limiting</h3>
                    <dl className="spec-list">
                        <dt>Total requests</dt>
                        <dd className="mono">{metricsData.rate_limiting.total_requests}</dd>
                        <dt>Rate limited</dt>
                        <dd className="mono">{metricsData.rate_limiting.rate_limited_requests}</dd>
                        <dt>Rate limit percentage</dt>
                        <dd className="mono">
                            {(metricsData.rate_limiting.rate_limit_percentage * 100).toFixed(2)}%
                        </dd>
                    </dl>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default RateLimitingMetrics
