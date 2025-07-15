import React, { useState, useEffect } from 'react';
import { 
    Container, 
    Row, 
    Col, 
    Card, 
    Alert, 
    Spinner,
    Badge,
    Table,
    Button,
    ProgressBar
} from 'react-bootstrap';
import { useAuth } from '../../contexts/AuthContext';
// Use environment variable from build time, fallback to /api for production
const API_URL = process.env.REACT_APP_API_URL || '/api';

const SystemInfo = () => {
    const { token } = useAuth();
    const [healthData, setHealthData] = useState(null);
    const [metricsData, setMetricsData] = useState(null);
    const [cacheStats, setCacheStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchSystemInfo();
    }, []);

    const fetchSystemInfo = async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch health data
            const healthResponse = await fetch(`${API_URL}/health/detailed`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (healthResponse.ok) {
                const health = await healthResponse.json();
                setHealthData(health);
            }

            // Fetch metrics data
            const metricsResponse = await fetch(`${API_URL}/metrics`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (metricsResponse.ok) {
                const metrics = await metricsResponse.json();
                setMetricsData(metrics);
            }

            // Fetch cache stats
            const cacheResponse = await fetch(`${API_URL}/cache/stats`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (cacheResponse.ok) {
                const cache = await cacheResponse.json();
                setCacheStats(cache);
            }

        } catch (error) {
            console.error('Error fetching system info:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const formatUptime = (seconds) => {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    };

    const getStatusBadge = (status) => {
        const statusMap = {
            'healthy': 'success',
            'degraded': 'warning',
            'unhealthy': 'danger',
            'critical': 'danger'
        };
        return <Badge bg={statusMap[status] || 'secondary'}>{status}</Badge>;
    };

    const flushCache = async () => {
        try {
            const response = await fetch(`${API_URL}/cache/flush`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                alert('Cache flushed successfully');
                fetchSystemInfo();
            } else {
                throw new Error('Failed to flush cache');
            }
        } catch (error) {
            console.error('Error flushing cache:', error);
            alert('Error flushing cache: ' + error.message);
        }
    };

    if (loading) {
        return (
            <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '300px' }}>
                <Spinner animation="border" variant="primary" />
            </Container>
        );
    }

    return (
        <Container>
            <Row className="mb-4">
                <Col>
                    <h2>System Information</h2>
                    <p className="text-muted">System health, performance metrics, and monitoring data</p>
                </Col>
                <Col xs="auto">
                    <Button variant="outline-primary" onClick={fetchSystemInfo}>
                        <i className="bi bi-arrow-clockwise me-2"></i>
                        Refresh
                    </Button>
                </Col>
            </Row>

            {error && (
                <Alert variant="danger" className="mb-4">
                    {error}
                </Alert>
            )}

            {/* System Health Overview */}
            {healthData && (
                <Row className="mb-4">
                    <Col md={3}>
                        <Card className="text-center">
                            <Card.Body>
                                <Card.Title>System Status</Card.Title>
                                {getStatusBadge(healthData.status)}
                                <div className="mt-2">
                                    <small className="text-muted">
                                        Last updated: {new Date(healthData.timestamp).toLocaleString()}
                                    </small>
                                </div>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={3}>
                        <Card className="text-center">
                            <Card.Body>
                                <Card.Title>Uptime</Card.Title>
                                <Card.Text className="h4">
                                    {formatUptime(healthData.uptime_seconds)}
                                </Card.Text>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={3}>
                        <Card className="text-center">
                            <Card.Body>
                                <Card.Title>Version</Card.Title>
                                <Card.Text className="h4">{healthData.version}</Card.Text>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={3}>
                        <Card className="text-center">
                            <Card.Body>
                                <Card.Title>Memory Usage</Card.Title>
                                <Card.Text className="h4">
                                    {healthData.system?.memory_usage_percent?.toFixed(1)}%
                                </Card.Text>
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>
            )}

            {/* Components Health */}
            {healthData?.components && (
                <Row className="mb-4">
                    <Col>
                        <Card>
                            <Card.Header>
                                <h5 className="mb-0">Components Health</h5>
                            </Card.Header>
                            <Card.Body>
                                <Table responsive>
                                    <thead>
                                        <tr>
                                            <th>Component</th>
                                            <th>Status</th>
                                            <th>Response Time</th>
                                            <th>Details</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {Object.entries(healthData.components).map(([component, data]) => (
                                            <tr key={component}>
                                                <td className="text-capitalize">{component}</td>
                                                <td>{getStatusBadge(data.status)}</td>
                                                <td>
                                                    {data.response_time_ms ? `${data.response_time_ms.toFixed(2)}ms` : 'N/A'}
                                                </td>
                                                <td>
                                                    {data.details && (
                                                        <small className="text-muted">
                                                            {typeof data.details === 'object' 
                                                                ? JSON.stringify(data.details, null, 2) 
                                                                : data.details}
                                                        </small>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </Table>
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>
            )}

            {/* Request Metrics */}
            {metricsData?.requests && (
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
            )}

            {/* Rate Limiting */}
            {metricsData?.rate_limiting && (
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
            )}

            {/* Cache Stats Details */}
            {cacheStats?.redis_stats && (
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
            )}
        </Container>
    );
};

export default SystemInfo;