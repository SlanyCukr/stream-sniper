'use client'
import {
    Row, Col, Card,
} from 'react-bootstrap'

/**
 * Redis Cache Details Component
 */
const RedisCacheDetails = ({
    cacheStats, formatUptime,
}) => (
    <Row className="mb-4">
        <Col>
            <Card>
                <Card.Body>
                    <h3 className="section-label mb-3">Redis cache</h3>
                    <dl className="spec-list">
                        <dt>Connected clients</dt>
                        <dd className="mono">{cacheStats.redis_stats.connected_clients}</dd>
                        <dt>Used memory</dt>
                        <dd className="mono">{cacheStats.redis_stats.used_memory_human}</dd>
                        <dt>Total keys</dt>
                        <dd className="mono">{cacheStats.redis_stats.total_keys}</dd>
                        <dt>Hit ratio</dt>
                        <dd className="mono">
                            {(cacheStats.redis_stats.keyspace_hit_ratio * 100).toFixed(2)}%
                        </dd>
                        <dt>Uptime</dt>
                        <dd className="mono">{formatUptime(cacheStats.redis_stats.uptime_in_seconds)}</dd>
                    </dl>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default RedisCacheDetails
