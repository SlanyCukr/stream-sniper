'use client'
import {
    Row, Col, Card,
} from 'react-bootstrap'

/**
 * In-process Cache Details Component
 */
const CacheDetails = ({
    cacheStats,
}) => (
    <Row className="mb-4">
        <Col>
            <Card>
                <Card.Body>
                    <h3 className="section-label mb-3">Cache</h3>
                    <dl className="spec-list">
                        <dt>Backend</dt>
                        <dd className="mono">{cacheStats.cache_stats.backend}</dd>
                        <dt>Status</dt>
                        <dd className="mono">{cacheStats.cache_stats.status}</dd>
                        <dt>Cached keys</dt>
                        <dd className="mono">{cacheStats.cache_stats.stream_sniper_keys}</dd>
                    </dl>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default CacheDetails
