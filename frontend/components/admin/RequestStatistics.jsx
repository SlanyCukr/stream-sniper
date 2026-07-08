'use client'
import {
    Row, Col, Card, Button,
} from 'react-bootstrap'

/**
 * Request and Cache Metrics Component
 */
const RequestStatistics = ({
    metricsData, flushCache,
}) => (
    <Row className="mb-4">
        <Col md={6}>
            <Card className="h-100">
                <Card.Body>
                    <h3 className="section-label mb-3">Request statistics</h3>
                    <div className="stat-grid">
                        <div className="stat-tile">
                            <div className="stat-label">Total requests</div>
                            <div className="stat-value mono">{metricsData.requests.total_requests}</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-label">Successful</div>
                            <div className="stat-value mono">{metricsData.requests.successful_requests}</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-label">Failed</div>
                            <div className="stat-value mono">{metricsData.requests.failed_requests}</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-label">Avg response</div>
                            <div className="stat-value mono">
                                {metricsData.requests.average_response_time_ms?.toFixed(2)}ms
                            </div>
                        </div>
                    </div>
                </Card.Body>
            </Card>
        </Col>
        <Col md={6}>
            <Card className="h-100">
                <Card.Body>
                    <h3 className="section-label mb-3">Cache performance</h3>
                    {metricsData.cache && (
                        <div className="stat-grid">
                            <div className="stat-tile">
                                <div className="stat-label">Hit rate</div>
                                <div className="stat-value text-phosphor mono">
                                    {(metricsData.cache.hit_rate * 100).toFixed(1)}%
                                </div>
                            </div>
                            <div className="stat-tile">
                                <div className="stat-label">Total hits</div>
                                <div className="stat-value mono">{metricsData.cache.total_hits}</div>
                            </div>
                            <div className="stat-tile">
                                <div className="stat-label">Total misses</div>
                                <div className="stat-value mono">{metricsData.cache.total_misses}</div>
                            </div>
                            <div className="stat-tile">
                                <div className="stat-label">Operations</div>
                                <div className="stat-value mono">{metricsData.cache.total_operations}</div>
                            </div>
                        </div>
                    )}
                    <div className="mt-3">
                        <Button
                            variant="outline-danger"
                            size="sm"
                            onClick={flushCache}
                        >
                            <i className="bi bi-trash3 me-1"></i>
                            Flush Cache
                        </Button>
                    </div>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default RequestStatistics
