'use client'
import {
    useState, useEffect, useCallback,
} from 'react'
import {
    Row, Col, Card, Alert, Spinner,
} from 'react-bootstrap'
import Link from 'next/link'
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
            <div
                className="d-flex justify-content-center align-items-center"
                style={{ minHeight: '300px' }}>
                <Spinner
                    animation="border"
                    variant="primary" />
            </div>
        )
    }

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Admin dashboard</h1>
                    <p className="page-sub">Welcome back, {user?.username}</p>
                </div>
            </div>

            {error && (
                <Alert
                    variant="danger"
                    className="mb-4">
                    {error}
                </Alert>
            )}

            {stats && (
                <div className="stat-grid mb-4">
                    <div className="stat-tile">
                        <div className="stat-label">Total users</div>
                        <div className="stat-value text-phosphor">{stats.total_users}</div>
                    </div>
                    <div className="stat-tile">
                        <div className="stat-label">Active users</div>
                        <div className="stat-value">{stats.active_users}</div>
                    </div>
                    <div className="stat-tile">
                        <div className="stat-label">Admin users</div>
                        <div className="stat-value">{stats.admin_users}</div>
                    </div>
                    <div className="stat-tile">
                        <div className="stat-label">Recent registrations</div>
                        <div className="stat-value">{stats.recent_registrations}</div>
                        <div className="stat-hint">Last 24 hours</div>
                    </div>
                </div>
            )}

            <Row>
                <Col md={6}>
                    <Card className="mb-4">
                        <Card.Body>
                            <h3 className="section-label mb-3">Quick actions</h3>
                            <div className="d-grid gap-2">
                                <Link
                                    href="/admin/users"
                                    className="btn btn-primary">
                                    <i
                                        className="bi bi-people me-2"
                                        aria-hidden="true" />
                                    Manage Users
                                </Link>
                                <Link
                                    href="/admin/users/create"
                                    className="btn btn-outline-primary">
                                    <i
                                        className="bi bi-person-plus me-2"
                                        aria-hidden="true" />
                                    Create New User
                                </Link>
                                <Link
                                    href="/admin/tracking"
                                    className="btn btn-outline-primary">
                                    <i
                                        className="bi bi-broadcast me-2"
                                        aria-hidden="true" />
                                    Stream Tracking
                                </Link>
                                <Link
                                    href="/admin/system"
                                    className="btn btn-outline-primary">
                                    <i
                                        className="bi bi-gear me-2"
                                        aria-hidden="true" />
                                    System Information
                                </Link>
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
                <Col md={6}>
                    <Card className="mb-4">
                        <Card.Body>
                            <h3 className="section-label mb-3">System status</h3>
                            <div className="mb-3">
                                <div className="d-flex justify-content-between align-items-center">
                                    <span>Database</span>
                                    <span className="status-chip is-ok">Online</span>
                                </div>
                            </div>
                            <div className="mb-3">
                                <div className="d-flex justify-content-between align-items-center">
                                    <span>API</span>
                                    <span className="status-chip is-ok">Healthy</span>
                                </div>
                            </div>
                            <div className="mb-3">
                                <div className="d-flex justify-content-between align-items-center">
                                    <span>Cache</span>
                                    <span className="status-chip is-ok">Active</span>
                                </div>
                            </div>
                            <div className="mb-3">
                                <div className="d-flex justify-content-between align-items-center">
                                    <span>User Activity</span>
                                    <span className="status-chip is-ok">Normal</span>
                                </div>
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
        </>
    )
}

export default AdminDashboard
