'use client'
import {
    useState, useEffect, useCallback,
} from 'react'
import {
    Container, Row, Col, Card, Alert, Spinner,
} from 'react-bootstrap'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/lib/api'

const AdminDashboard = () => {
    const { user } = useAuth()
    const [
        stats,
        setStats,
    ] = useState(null)
    const [
        loading,
        setLoading,
    ] = useState(true)
    const [
        error,
        setError,
    ] = useState(null)

    const fetchSystemStats = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            const { data } = await api.get('/auth/admin/stats')
            setStats(data)
        } catch (fetchError) {
            console.error('Error fetching system stats:', fetchError)
            setError(fetchError.response?.data?.detail || fetchError.message || 'Failed to fetch system stats')
        } finally {
            setLoading(false)
        }
    }, [
    ])

    useEffect(() => {
        fetchSystemStats()
    }, [
        fetchSystemStats,
    ])

    if (loading) {
        return (
            <Container
                className="d-flex justify-content-center align-items-center"
                style={{ minHeight: '300px' }}>
                <Spinner
                    animation="border"
                    variant="primary" />
            </Container>
        )
    }

    return (
        <Container>
            <Row className="mb-4">
                <Col>
                    <h2>Admin Dashboard</h2>
                    <p className="text-muted">Welcome back, {user?.username}!</p>
                </Col>
            </Row>

            {error && (
                <Alert
                    variant="danger"
                    className="mb-4">
                    {error}
                </Alert>
            )}

            {stats && (
                <Row className="mb-4">
                    <Col md={3}>
                        <Card className="text-center">
                            <Card.Body>
                                <Card.Title className="text-primary">Total Users</Card.Title>
                                <Card.Text className="display-4">{stats.total_users}</Card.Text>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={3}>
                        <Card className="text-center">
                            <Card.Body>
                                <Card.Title className="text-success">Active Users</Card.Title>
                                <Card.Text className="display-4">{stats.active_users}</Card.Text>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={3}>
                        <Card className="text-center">
                            <Card.Body>
                                <Card.Title className="text-warning">Admin Users</Card.Title>
                                <Card.Text className="display-4">{stats.admin_users}</Card.Text>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={3}>
                        <Card className="text-center">
                            <Card.Body>
                                <Card.Title className="text-info">Recent Registrations</Card.Title>
                                <Card.Text className="display-4">{stats.recent_registrations}</Card.Text>
                                <small className="text-muted">Last 24 hours</small>
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>
            )}

            <Row>
                <Col md={6}>
                    <Card>
                        <Card.Header>
                            <Card.Title>Quick Actions</Card.Title>
                        </Card.Header>
                        <Card.Body>
                            <div className="d-grid gap-2">
                                <a
                                    href="/admin/users"
                                    className="btn btn-primary">
                                    <i className="bi bi-people me-2"></i>
                                    Manage Users
                                </a>
                                <a
                                    href="/admin/users/create"
                                    className="btn btn-success">
                                    <i className="bi bi-person-plus me-2"></i>
                                    Create New User
                                </a>
                                <a
                                    href="/admin/tracking"
                                    className="btn btn-warning">
                                    <i className="bi bi-broadcast me-2"></i>
                                    Stream Tracking
                                </a>
                                <a
                                    href="/admin/system"
                                    className="btn btn-info">
                                    <i className="bi bi-gear me-2"></i>
                                    System Information
                                </a>
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={6}>
                    <Card>
                        <Card.Header>
                            <Card.Title>System Status</Card.Title>
                        </Card.Header>
                        <Card.Body>
                            <div className="mb-3">
                                <div className="d-flex justify-content-between">
                                    <span>Database</span>
                                    <span className="badge bg-success">Online</span>
                                </div>
                            </div>
                            <div className="mb-3">
                                <div className="d-flex justify-content-between">
                                    <span>API</span>
                                    <span className="badge bg-success">Healthy</span>
                                </div>
                            </div>
                            <div className="mb-3">
                                <div className="d-flex justify-content-between">
                                    <span>Cache</span>
                                    <span className="badge bg-success">Active</span>
                                </div>
                            </div>
                            <div className="mb-3">
                                <div className="d-flex justify-content-between">
                                    <span>User Activity</span>
                                    <span className="badge bg-success">Normal</span>
                                </div>
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </Container>
    )
}

export default AdminDashboard
