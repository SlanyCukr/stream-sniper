import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Alert, Spinner, Badge, ProgressBar } from 'react-bootstrap';
import { useAuth } from '../../contexts/AuthContext';
import env from 'react-dotenv';

const TrackingDashboard = () => {
    const { user, token } = useAuth();
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 30000); // Update every 30 seconds
        return () => clearInterval(interval);
    }, []);

    const fetchStats = async () => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch(`${env.API_URL}/admin/tracking/stats`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                setStats(data);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch stats');
            }
        } catch (error) {
            console.error('Error fetching stats:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const getHealthBadge = (isHealthy) => {
        return isHealthy ? 
            <Badge bg="success">Healthy</Badge> : 
            <Badge bg="danger">Unhealthy</Badge>;
    };

    const getStatusBadge = (isActive) => {
        return isActive ? 
            <Badge bg="success">Active</Badge> : 
            <Badge bg="secondary">Inactive</Badge>;
    };

    const calculateSuccessRate = (completed, total) => {
        if (total === 0) return 0;
        return Math.round((completed / total) * 100);
    };

    if (loading && !stats) {
        return (
            <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '300px' }}>
                <Spinner animation="border" variant="primary" />
            </Container>
        );
    }

    return (
        <Container fluid>
            <Row className="mb-4">
                <Col>
                    <h2>Tracking Dashboard</h2>
                    <p className="text-muted">
                        Overview of automated stream tracking and processing system
                        {stats && <small className="ms-2">Last updated: {new Date().toLocaleTimeString()}</small>}
                    </p>
                </Col>
            </Row>

            {error && (
                <Alert variant="danger" className="mb-4" dismissible onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {stats && (
                <>
                    {/* System Status Row */}
                    <Row className="mb-4">
                        <Col md={4}>
                            <Card>
                                <Card.Body>
                                    <h5>System Status</h5>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Stream Monitoring</span>
                                            {getStatusBadge(stats.system_status.monitoring_active)}
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Processing Queue</span>
                                            <Badge bg={stats.system_status.processing_queue_size > 0 ? 'warning' : 'success'}>
                                                {stats.system_status.processing_queue_size} pending
                                            </Badge>
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Failed Jobs</span>
                                            <Badge bg={stats.system_status.failed_jobs > 0 ? 'danger' : 'success'}>
                                                {stats.system_status.failed_jobs}
                                            </Badge>
                                        </div>
                                    </div>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={4}>
                            <Card>
                                <Card.Body>
                                    <h5>Tracked Streamers</h5>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Total Streamers</span>
                                            <Badge bg="primary">{stats.tracked_streamers.total}</Badge>
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Active</span>
                                            <Badge bg="success">{stats.tracked_streamers.active}</Badge>
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Processing Enabled</span>
                                            <Badge bg="info">{stats.tracked_streamers.processing_enabled}</Badge>
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Inactive</span>
                                            <Badge bg="secondary">{stats.tracked_streamers.inactive}</Badge>
                                        </div>
                                    </div>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={4}>
                            <Card>
                                <Card.Body>
                                    <h5>Processing Overview</h5>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Success Rate</span>
                                            <Badge bg="success">
                                                {calculateSuccessRate(stats.processing_jobs.completed, stats.processing_jobs.total)}%
                                            </Badge>
                                        </div>
                                        <ProgressBar 
                                            now={calculateSuccessRate(stats.processing_jobs.completed, stats.processing_jobs.total)}
                                            variant="success"
                                            className="mt-2"
                                        />
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Recent Activity</span>
                                            <Badge bg="info">{stats.processing_jobs.recent_24h} jobs (24h)</Badge>
                                        </div>
                                    </div>
                                </Card.Body>
                            </Card>
                        </Col>
                    </Row>

                    {/* Processing Jobs Statistics */}
                    <Row className="mb-4">
                        <Col>
                            <Card>
                                <Card.Header>
                                    <Card.Title>Processing Jobs Statistics</Card.Title>
                                </Card.Header>
                                <Card.Body>
                                    <Row>
                                        <Col md={2}>
                                            <Card className="text-center bg-light">
                                                <Card.Body>
                                                    <Card.Title className="text-primary">Total</Card.Title>
                                                    <Card.Text className="display-6">{stats.processing_jobs.total}</Card.Text>
                                                </Card.Body>
                                            </Card>
                                        </Col>
                                        <Col md={2}>
                                            <Card className="text-center bg-light">
                                                <Card.Body>
                                                    <Card.Title className="text-secondary">Pending</Card.Title>
                                                    <Card.Text className="display-6">{stats.processing_jobs.pending || 0}</Card.Text>
                                                </Card.Body>
                                            </Card>
                                        </Col>
                                        <Col md={2}>
                                            <Card className="text-center bg-light">
                                                <Card.Body>
                                                    <Card.Title className="text-primary">In Progress</Card.Title>
                                                    <Card.Text className="display-6">{stats.processing_jobs.in_progress || 0}</Card.Text>
                                                </Card.Body>
                                            </Card>
                                        </Col>
                                        <Col md={2}>
                                            <Card className="text-center bg-light">
                                                <Card.Body>
                                                    <Card.Title className="text-success">Completed</Card.Title>
                                                    <Card.Text className="display-6">{stats.processing_jobs.completed || 0}</Card.Text>
                                                </Card.Body>
                                            </Card>
                                        </Col>
                                        <Col md={2}>
                                            <Card className="text-center bg-light">
                                                <Card.Body>
                                                    <Card.Title className="text-danger">Failed</Card.Title>
                                                    <Card.Text className="display-6">{stats.processing_jobs.failed || 0}</Card.Text>
                                                </Card.Body>
                                            </Card>
                                        </Col>
                                        <Col md={2}>
                                            <Card className="text-center bg-light">
                                                <Card.Body>
                                                    <Card.Title className="text-info">Recent 24h</Card.Title>
                                                    <Card.Text className="display-6">{stats.processing_jobs.recent_24h || 0}</Card.Text>
                                                </Card.Body>
                                            </Card>
                                        </Col>
                                    </Row>
                                </Card.Body>
                            </Card>
                        </Col>
                    </Row>

                    {/* Quick Actions */}
                    <Row>
                        <Col md={6}>
                            <Card>
                                <Card.Header>
                                    <Card.Title>Quick Actions</Card.Title>
                                </Card.Header>
                                <Card.Body>
                                    <div className="d-grid gap-2">
                                        <a href="/admin/tracking/streamers" className="btn btn-primary">
                                            <i className="bi bi-people me-2"></i>
                                            Manage Tracked Streamers
                                        </a>
                                        <a href="/admin/tracking/jobs" className="btn btn-info">
                                            <i className="bi bi-list-check me-2"></i>
                                            View Processing Jobs
                                        </a>
                                        <button 
                                            className="btn btn-success" 
                                            onClick={fetchStats}
                                            disabled={loading}
                                        >
                                            <i className="bi bi-arrow-clockwise me-2"></i>
                                            Refresh Statistics
                                        </button>
                                    </div>
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col md={6}>
                            <Card>
                                <Card.Header>
                                    <Card.Title>System Health</Card.Title>
                                </Card.Header>
                                <Card.Body>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Overall System</span>
                                            {getHealthBadge(
                                                stats.system_status.monitoring_active && 
                                                stats.system_status.failed_jobs === 0
                                            )}
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Stream Monitoring</span>
                                            {getHealthBadge(stats.system_status.monitoring_active)}
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Processing Queue</span>
                                            {getHealthBadge(stats.system_status.processing_queue_size < 100)}
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <div className="d-flex justify-content-between">
                                            <span>Error Rate</span>
                                            {getHealthBadge(stats.system_status.failed_jobs < 10)}
                                        </div>
                                    </div>
                                </Card.Body>
                            </Card>
                        </Col>
                    </Row>
                </>
            )}
        </Container>
    );
};

export default TrackingDashboard;