'use client'
import {
    Row, Col, Card, Table,
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
                <Card.Header>
                    <h5 className="mb-0">Redis Cache Details</h5>
                </Card.Header>
                <Card.Body>
                    <Table responsive>
                        <tbody>
                            <tr>
                                <td>Connected Clients</td>
                                <td>{cacheStats.redis_stats.connected_clients}</td>
                            </tr>
                            <tr>
                                <td>Used Memory</td>
                                <td>{cacheStats.redis_stats.used_memory_human}</td>
                            </tr>
                            <tr>
                                <td>Total Keys</td>
                                <td>{cacheStats.redis_stats.total_keys}</td>
                            </tr>
                            <tr>
                                <td>Hit Ratio</td>
                                <td>{(cacheStats.redis_stats.keyspace_hit_ratio * 100).toFixed(2)}%</td>
                            </tr>
                            <tr>
                                <td>Uptime</td>
                                <td>{formatUptime(cacheStats.redis_stats.uptime_in_seconds)}</td>
                            </tr>
                        </tbody>
                    </Table>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default RedisCacheDetails
