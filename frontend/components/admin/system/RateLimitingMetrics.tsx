'use client'
import {
    Row, Col, Card,
} from 'react-bootstrap'
import type { SystemMetrics } from '@/hooks/admin/system/useSystemQueries'

interface RateLimitingMetricsProps {
    rateLimiting: SystemMetrics['rateLimiting']
}

const RateLimitingMetrics = ({ rateLimiting }: RateLimitingMetricsProps) => (
    <Row className="mb-4">
        <Col>
            <Card>
                <Card.Body>
                    <h3 className="section-label mb-3">Rate limiting</h3>
                    <dl className="spec-list">
                        <dt>Total requests</dt>
                        <dd className="mono">{rateLimiting.totalRequests}</dd>
                        <dt>Rate limited</dt>
                        <dd className="mono">{rateLimiting.rateLimitedRequests}</dd>
                        <dt>Rate limit percentage</dt>
                        <dd className="mono">
                            {(rateLimiting.rateLimitPercentage * 100).toFixed(2)}%
                        </dd>
                    </dl>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default RateLimitingMetrics
