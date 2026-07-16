'use client'
import {
    Row, Col, Card, Button,
} from 'react-bootstrap'

const RequestStatistics = ({
    requests, cache, flushCache,
}) => (
    <Row className="mb-4">
        <Col md={6}>
            <Card className="h-100">
                <Card.Body>
                    <h3 className="section-label mb-3">Request statistics</h3>
                    <div className="stat-grid">
                        <div className="stat-tile">
                            <div className="stat-label">Total requests</div>
                            <div className="stat-value mono">{requests.totalRequests}</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-label">Successful</div>
                            <div className="stat-value mono">{requests.successfulRequests}</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-label">Failed</div>
                            <div className="stat-value mono">{requests.failedRequests}</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-label">Avg response</div>
                            <div className="stat-value mono">
                                {requests.averageResponseTimeMs?.toFixed(2)}ms
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
                    {cache && (
                        <div className="stat-grid">
                            <div className="stat-tile">
                                <div className="stat-label">Hit rate</div>
                                <div className="stat-value text-phosphor mono">
                                    {(cache.hitRate * 100).toFixed(1)}%
                                </div>
                            </div>
                            <div className="stat-tile">
                                <div className="stat-label">Total hits</div>
                                <div className="stat-value mono">{cache.totalHits}</div>
                            </div>
                            <div className="stat-tile">
                                <div className="stat-label">Total misses</div>
                                <div className="stat-value mono">{cache.totalMisses}</div>
                            </div>
                            <div className="stat-tile">
                                <div className="stat-label">Operations</div>
                                <div className="stat-value mono">{cache.totalOperations}</div>
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
