'use client'

import {
    Form, Row, Col,
} from 'react-bootstrap'

/**
 * Profile Info Display Component
 */
const ProfileInfo = ({
    user, formData, handleChange, isEditing, isSubmitting, loading,
}) => (
    <>
        <Row>
            <Col md={6}>
                <Form.Group className="mb-3">
                    <Form.Label>Username</Form.Label>
                    <Form.Control
                        type="text"
                        value={user?.username || ''}
                        disabled
                    />
                    <small className="text-muted">Username cannot be changed</small>
                </Form.Group>
            </Col>
            <Col md={6}>
                <Form.Group className="mb-3">
                    <Form.Label>Role</Form.Label>
                    <div>
                        <span className={user?.role === 'admin' ? 'status-chip is-warn' : 'status-chip is-ok'}>
                            {user?.role || 'user'}
                        </span>
                    </div>
                </Form.Group>
            </Col>
        </Row>

        <Form.Group className="mb-3">
            <Form.Label htmlFor="email">Email</Form.Label>
            <Form.Control
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Enter your email address"
                disabled={!isEditing || isSubmitting || loading}
                required
            />
        </Form.Group>

        <Row>
            <Col md={6}>
                <Form.Group className="mb-3">
                    <Form.Label>Account Status</Form.Label>
                    <div>
                        <span className={user?.is_active ? 'status-chip is-ok' : 'status-chip is-err'}>
                            {user?.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                </Form.Group>
            </Col>
            <Col md={6}>
                <Form.Group className="mb-3">
                    <Form.Label>Member Since</Form.Label>
                    <div className="mono text-muted small pt-1">
                        {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                    </div>
                </Form.Group>
            </Col>
        </Row>
    </>
)

export default ProfileInfo
