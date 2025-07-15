import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Table, Button, Alert, Spinner, Badge, Modal, Form, Pagination } from 'react-bootstrap';
import { useAuth } from '../../contexts/AuthContext';
import env from 'react-dotenv';

const StreamerTracking = () => {
    const { user, token } = useAuth();
    const [streamers, setStreamers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [pagination, setPagination] = useState({
        offset: 0,
        limit: 20,
        total: 0,
        currentPage: 1
    });
    const [filters, setFilters] = useState({
        is_active: null,
        processing_enabled: null
    });
    const [newStreamer, setNewStreamer] = useState({
        twitch_username: '',
        notes: '',
        is_active: true,
        processing_enabled: true
    });
    const [formSubmitting, setFormSubmitting] = useState(false);

    useEffect(() => {
        fetchStreamers();
    }, [pagination.offset, pagination.limit, filters]);

    const fetchStreamers = async () => {
        try {
            setLoading(true);
            setError(null);

            const params = new URLSearchParams({
                offset: pagination.offset.toString(),
                limit: pagination.limit.toString()
            });

            if (filters.is_active !== null) {
                params.append('is_active', filters.is_active.toString());
            }
            if (filters.processing_enabled !== null) {
                params.append('processing_enabled', filters.processing_enabled.toString());
            }

            const response = await fetch(`${env.API_URL}/admin/tracking/streamers?${params}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                setStreamers(data.streamers);
                setPagination(prev => ({
                    ...prev,
                    total: data.total,
                    currentPage: Math.floor(data.offset / data.limit) + 1
                }));
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch streamers');
            }
        } catch (error) {
            console.error('Error fetching streamers:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleAddStreamer = async (e) => {
        e.preventDefault();
        try {
            setFormSubmitting(true);
            setError(null);

            const response = await fetch(`${env.API_URL}/admin/tracking/streamers`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newStreamer)
            });

            if (response.ok) {
                setSuccess('Streamer added successfully');
                setShowAddModal(false);
                setNewStreamer({
                    twitch_username: '',
                    notes: '',
                    is_active: true,
                    processing_enabled: true
                });
                fetchStreamers();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to add streamer');
            }
        } catch (error) {
            console.error('Error adding streamer:', error);
            setError(error.message);
        } finally {
            setFormSubmitting(false);
        }
    };

    const handleToggleActive = async (streamerId, currentStatus) => {
        try {
            const response = await fetch(`${env.API_URL}/admin/tracking/streamers/${streamerId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    is_active: !currentStatus
                })
            });

            if (response.ok) {
                setSuccess('Streamer updated successfully');
                fetchStreamers();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to update streamer');
            }
        } catch (error) {
            console.error('Error updating streamer:', error);
            setError(error.message);
        }
    };

    const handleToggleProcessing = async (streamerId, currentStatus) => {
        try {
            const response = await fetch(`${env.API_URL}/admin/tracking/streamers/${streamerId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    processing_enabled: !currentStatus
                })
            });

            if (response.ok) {
                setSuccess('Streamer updated successfully');
                fetchStreamers();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to update streamer');
            }
        } catch (error) {
            console.error('Error updating streamer:', error);
            setError(error.message);
        }
    };

    const handleRemoveStreamer = async (streamerId, username) => {
        if (!window.confirm(`Are you sure you want to remove ${username} from tracking?`)) {
            return;
        }

        try {
            const response = await fetch(`${env.API_URL}/admin/tracking/streamers/${streamerId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                setSuccess('Streamer removed successfully');
                fetchStreamers();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to remove streamer');
            }
        } catch (error) {
            console.error('Error removing streamer:', error);
            setError(error.message);
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
        if (!dateString) return 'Never';
        return new Date(dateString).toLocaleString();
    };

    const getStatusBadge = (isActive) => {
        return isActive ? 
            <Badge bg="success">Active</Badge> : 
            <Badge bg="secondary">Inactive</Badge>;
    };

    const getProcessingBadge = (isEnabled) => {
        return isEnabled ? 
            <Badge bg="primary">Enabled</Badge> : 
            <Badge bg="warning">Disabled</Badge>;
    };

    const totalPages = Math.ceil(pagination.total / pagination.limit);

    return (
        <Container fluid>
            <Row className="mb-4">
                <Col>
                    <h2>Streamer Tracking</h2>
                    <p className="text-muted">Manage automated tracking of Twitch streamers</p>
                </Col>
                <Col xs="auto">
                    <Button 
                        variant="primary" 
                        onClick={() => setShowAddModal(true)}
                        disabled={loading}
                    >
                        <i className="bi bi-plus-circle me-2"></i>
                        Add Streamer
                    </Button>
                </Col>
            </Row>

            {error && (
                <Alert variant="danger" className="mb-4" dismissible onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {success && (
                <Alert variant="success" className="mb-4" dismissible onClose={() => setSuccess(null)}>
                    {success}
                </Alert>
            )}

            <Row className="mb-4">
                <Col md={4}>
                    <Card>
                        <Card.Body>
                            <h5>Filters</h5>
                            <Form>
                                <Form.Group className="mb-3">
                                    <Form.Label>Status</Form.Label>
                                    <Form.Select 
                                        value={filters.is_active === null ? '' : filters.is_active.toString()}
                                        onChange={(e) => setFilters(prev => ({
                                            ...prev,
                                            is_active: e.target.value === '' ? null : e.target.value === 'true'
                                        }))}
                                    >
                                        <option value="">All</option>
                                        <option value="true">Active</option>
                                        <option value="false">Inactive</option>
                                    </Form.Select>
                                </Form.Group>
                                <Form.Group className="mb-3">
                                    <Form.Label>Processing</Form.Label>
                                    <Form.Select 
                                        value={filters.processing_enabled === null ? '' : filters.processing_enabled.toString()}
                                        onChange={(e) => setFilters(prev => ({
                                            ...prev,
                                            processing_enabled: e.target.value === '' ? null : e.target.value === 'true'
                                        }))}
                                    >
                                        <option value="">All</option>
                                        <option value="true">Enabled</option>
                                        <option value="false">Disabled</option>
                                    </Form.Select>
                                </Form.Group>
                            </Form>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={8}>
                    <Card>
                        <Card.Header>
                            <Card.Title>Tracked Streamers ({pagination.total})</Card.Title>
                        </Card.Header>
                        <Card.Body>
                            {loading ? (
                                <div className="text-center">
                                    <Spinner animation="border" variant="primary" />
                                </div>
                            ) : streamers.length === 0 ? (
                                <Alert variant="info">No streamers found</Alert>
                            ) : (
                                <>
                                    <Table striped bordered hover responsive>
                                        <thead>
                                            <tr>
                                                <th>Username</th>
                                                <th>Display Name</th>
                                                <th>Status</th>
                                                <th>Processing</th>
                                                <th>Last Check</th>
                                                <th>Created</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {streamers.map(streamer => (
                                                <tr key={streamer.id}>
                                                    <td>
                                                        <strong>{streamer.twitch_username}</strong>
                                                    </td>
                                                    <td>{streamer.display_name}</td>
                                                    <td>{getStatusBadge(streamer.is_active)}</td>
                                                    <td>{getProcessingBadge(streamer.processing_enabled)}</td>
                                                    <td>{formatDateTime(streamer.last_stream_check)}</td>
                                                    <td>{formatDateTime(streamer.created_at)}</td>
                                                    <td>
                                                        <Button
                                                            variant={streamer.is_active ? "warning" : "success"}
                                                            size="sm"
                                                            className="me-2"
                                                            onClick={() => handleToggleActive(streamer.id, streamer.is_active)}
                                                        >
                                                            {streamer.is_active ? "Deactivate" : "Activate"}
                                                        </Button>
                                                        <Button
                                                            variant={streamer.processing_enabled ? "secondary" : "primary"}
                                                            size="sm"
                                                            className="me-2"
                                                            onClick={() => handleToggleProcessing(streamer.id, streamer.processing_enabled)}
                                                        >
                                                            {streamer.processing_enabled ? "Disable" : "Enable"}
                                                        </Button>
                                                        <Button
                                                            variant="danger"
                                                            size="sm"
                                                            onClick={() => handleRemoveStreamer(streamer.id, streamer.twitch_username)}
                                                        >
                                                            Remove
                                                        </Button>
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

            {/* Add Streamer Modal */}
            <Modal show={showAddModal} onHide={() => setShowAddModal(false)}>
                <Modal.Header closeButton>
                    <Modal.Title>Add Streamer to Tracking</Modal.Title>
                </Modal.Header>
                <Form onSubmit={handleAddStreamer}>
                    <Modal.Body>
                        <Form.Group className="mb-3">
                            <Form.Label>Twitch Username *</Form.Label>
                            <Form.Control
                                type="text"
                                value={newStreamer.twitch_username}
                                onChange={(e) => setNewStreamer(prev => ({
                                    ...prev,
                                    twitch_username: e.target.value
                                }))}
                                required
                                placeholder="Enter Twitch username"
                            />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Label>Notes</Form.Label>
                            <Form.Control
                                as="textarea"
                                rows={3}
                                value={newStreamer.notes}
                                onChange={(e) => setNewStreamer(prev => ({
                                    ...prev,
                                    notes: e.target.value
                                }))}
                                placeholder="Optional notes about this streamer"
                            />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Check
                                type="checkbox"
                                label="Active"
                                checked={newStreamer.is_active}
                                onChange={(e) => setNewStreamer(prev => ({
                                    ...prev,
                                    is_active: e.target.checked
                                }))}
                            />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Check
                                type="checkbox"
                                label="Processing Enabled"
                                checked={newStreamer.processing_enabled}
                                onChange={(e) => setNewStreamer(prev => ({
                                    ...prev,
                                    processing_enabled: e.target.checked
                                }))}
                            />
                        </Form.Group>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button variant="secondary" onClick={() => setShowAddModal(false)}>
                            Cancel
                        </Button>
                        <Button variant="primary" type="submit" disabled={formSubmitting}>
                            {formSubmitting ? (
                                <>
                                    <Spinner animation="border" size="sm" className="me-2" />
                                    Adding...
                                </>
                            ) : (
                                'Add Streamer'
                            )}
                        </Button>
                    </Modal.Footer>
                </Form>
            </Modal>
        </Container>
    );
};

export default StreamerTracking;