'use client'

import {
    Form, Row, Col,
} from 'react-bootstrap'
import { isAdminRole, USER_ROLES } from '@/lib/auth/roles'
import AuthFormField from '../shared/AuthFormField'

const ProfileInfo = ({
    user, formData, handleChange, isEditing, isSubmitting,
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
                        <span className={isAdminRole(user?.role) ? 'status-chip is-warn' : 'status-chip is-ok'}>
                            {user?.role || USER_ROLES.USER}
                        </span>
                    </div>
                </Form.Group>
            </Col>
        </Row>

        <AuthFormField
            label="Email"
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="Enter your email address"
            disabled={!isEditing || isSubmitting}
        />

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
