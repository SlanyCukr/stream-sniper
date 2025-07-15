import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Table, Alert, Spinner, Badge, Form, Pagination } from 'react-bootstrap';
import { useAuth } from '../../contexts/AuthContext';
// Use environment variable from build time, fallback to /api for production
const API_URL = process.env.REACT_APP_API_URL || '/api';

const ProcessingJobs = () => {
    const { user, token } = useAuth();
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [pagination, setPagination] = useState({
        offset: 0,
        limit: 50,
        total: 0,
        currentPage: 1
    });
    const [filters, setFilters] = useState({
        status: '',
        tracked_streamer_id: ''
    });
    const [stats, setStats] = useState({});

    useEffect(() => {
        fetchJobs();
        fetchStats();
    }, [pagination.offset, pagination.limit, filters]);

    const fetchJobs = async () => {
        try {
            setLoading(true);
            setError(null);

            const params = new URLSearchParams({
                offset: pagination.offset.toString(),
                limit: pagination.limit.toString()
            });

            if (filters.status) {
                params.append('status', filters.status);
            }
            if (filters.tracked_streamer_id) {
                params.append('tracked_streamer_id', filters.tracked_streamer_id);
            }

            const response = await fetch(`${API_URL}/admin/tracking/jobs?${params}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                setJobs(data.jobs);
                setPagination(prev => ({
                    ...prev,
                    total: data.total,
                    currentPage: Math.floor(data.offset / data.limit) + 1
                }));
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch jobs');
            }
        } catch (error) {
            console.error('Error fetching jobs:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const fetchStats = async () => {
        try {
            const response = await fetch(`${API_URL}/admin/tracking/stats`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                setStats(data.processing_jobs);
            }
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    };

    const handlePageChange = (page) => {
        setPagination(prev => ({
            ...prev,
            offset: (page - 1) * prev.limit,
            currentPage: page
        }));
    };

    const formatDateTime = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleString();
    };

    const getDuration = (startTime, endTime) => {
        if (!startTime || !endTime) return 'N/A';
        const start = new Date(startTime);
        const end = new Date(endTime);
        const duration = Math.floor((end - start) / 1000);
        return `${duration}s`;
    };

    const getStatusBadge = (status) => {
        const variants = {
            'pending': 'secondary',
            'in_progress': 'primary',
            'completed': 'success',
            'failed': 'danger'
        };
        return <Badge bg={variants[status] || 'secondary'}>{status}</Badge>;
    };

    const totalPages = Math.ceil(pagination.total / pagination.limit);

    return (
        <Container fluid>
            <Row className="mb-4">
                <Col>
                    <h2>Processing Jobs</h2>
                    <p className="text-muted">Monitor stream processing jobs and their status</p>
                </Col>
            </Row>

            {error && (
                <Alert variant="danger" className="mb-4" dismissible onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {/* Statistics Cards */}
            <Row className="mb-4">
                <Col md={2}>
                    <Card className="text-center">
                        <Card.Body>
                            <Card.Title className="text-primary">Total</Card.Title>
                            <Card.Text className="display-6">{stats.total || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={2}>
                    <Card className="text-center">
                        <Card.Body>
                            <Card.Title className="text-secondary">Pending</Card.Title>
                            <Card.Text className="display-6">{stats.pending || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={2}>
                    <Card className="text-center">
                        <Card.Body>
                            <Card.Title className="text-primary">In Progress</Card.Title>
                            <Card.Text className="display-6">{stats.in_progress || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={2}>
                    <Card className="text-center">
                        <Card.Body>
                            <Card.Title className="text-success">Completed</Card.Title>
                            <Card.Text className="display-6">{stats.completed || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={2}>
                    <Card className="text-center">
                        <Card.Body>
                            <Card.Title className="text-danger">Failed</Card.Title>
                            <Card.Text className="display-6">{stats.failed || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={2}>
                    <Card className="text-center">
                        <Card.Body>
                            <Card.Title className="text-info">Recent 24h</Card.Title>
                            <Card.Text className="display-6">{stats.recent_24h || 0}</Card.Text>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            <Row>
                <Col md={3}>
                    <Card>
                        <Card.Body>
                            <h5>Filters</h5>
                            <Form>
                                <Form.Group className="mb-3">
                                    <Form.Label>Status</Form.Label>
                                    <Form.Select 
                                        value={filters.status}
                                        onChange={(e) => setFilters(prev => ({
                                            ...prev,
                                            status: e.target.value
                                        }))}
                                    >
                                        <option value="">All</option>
                                        <option value="pending">Pending</option>
                                        <option value="in_progress">In Progress</option>
                                        <option value="completed">Completed</option>
                                        <option value="failed">Failed</option>
                                    </Form.Select>
                                </Form.Group>
                                <Form.Group className="mb-3">
                                    <Form.Label>Streamer ID</Form.Label>
                                    <Form.Control 
                                        type="number"
                                        value={filters.tracked_streamer_id}
                                        onChange={(e) => setFilters(prev => ({
                                            ...prev,
                                            tracked_streamer_id: e.target.value
                                        }))}
                                        placeholder="Filter by streamer ID"
                                    />
                                </Form.Group>
                            </Form>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={9}>
                    <Card>
                        <Card.Header>
                            <Card.Title>Processing Jobs ({pagination.total})</Card.Title>
                        </Card.Header>
                        <Card.Body>
                            {loading ? (
                                <div className="text-center">
                                    <Spinner animation="border" variant="primary" />
                                </div>
                            ) : jobs.length === 0 ? (
                                <Alert variant="info">No processing jobs found</Alert>
                            ) : (
                                <>
                                    <Table striped bordered hover responsive>
                                        <thead>
                                            <tr>
                                                <th>ID</th>
                                                <th>Streamer</th>
                                                <th>Stream ID</th>
                                                <th>Status</th>
                                                <th>Created</th>
                                                <th>Started</th>
                                                <th>Completed</th>
                                                <th>Duration</th>
                                                <th>Retries</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {jobs.map(job => (
                                                <tr key={job.id}>
                                                    <td>{job.id}</td>
                                                    <td>
                                                        <strong>{job.twitch_username}</strong>
                                                        {job.streamer_display_name && (
                                                            <small className="text-muted d-block">
                                                                {job.streamer_display_name}
                                                            </small>
                                                        )}
                                                    </td>
                                                    <td>{job.twitch_stream_id}</td>
                                                    <td>{getStatusBadge(job.status)}</td>
                                                    <td>{formatDateTime(job.created_at)}</td>
                                                    <td>{formatDateTime(job.started_at)}</td>
                                                    <td>{formatDateTime(job.completed_at)}</td>
                                                    <td>{getDuration(job.started_at, job.completed_at)}</td>
                                                    <td>
                                                        {job.retry_count > 0 && (
                                                            <Badge bg="warning">{job.retry_count}</Badge>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </Table>

                                    {totalPages > 1 && (
                                        <Pagination className="justify-content-center">
                                            <Pagination.First
                                                onClick={() => handlePageChange(1)}
                                                disabled={pagination.currentPage === 1}
                                            />
                                            <Pagination.Prev
                                                onClick={() => handlePageChange(pagination.currentPage - 1)}
                                                disabled={pagination.currentPage === 1}
                                            />
                                            {[...Array(Math.min(5, totalPages))].map((_, i) => {
                                                const page = Math.max(1, pagination.currentPage - 2) + i;
                                                if (page <= totalPages) {
                                                    return (
                                                        <Pagination.Item
                                                            key={page}
                                                            active={page === pagination.currentPage}
                                                            onClick={() => handlePageChange(page)}
                                                        >
                                                            {page}
                                                        </Pagination.Item>
                                                    );
                                                }
                                                return null;
                                            })}
                                            <Pagination.Next
                                                onClick={() => handlePageChange(pagination.currentPage + 1)}
                                                disabled={pagination.currentPage === totalPages}
                                            />
                                            <Pagination.Last
                                                onClick={() => handlePageChange(totalPages)}
                                                disabled={pagination.currentPage === totalPages}
                                            />
                                        </Pagination>
                                    )}
                                </>
                            )}
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </Container>
    );
};

export default ProcessingJobs;