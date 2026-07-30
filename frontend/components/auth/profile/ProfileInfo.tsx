'use client'

import type { ChangeEvent } from 'react'
import {
    Form, Row, Col,
} from 'react-bootstrap'
import { isAdminRole, USER_ROLES } from '@/lib/auth/roles'
import StatusChip from '@/components/common/StatusChip'
import type { AuthUser } from '@/lib/auth/service'
import AuthFormField from '../shared/AuthFormField'

interface ProfileInfoProps {
    user: AuthUser | null
    formData: { email: string }
    onEmailChange: (event: ChangeEvent<HTMLInputElement>) => void
    isEditing: boolean
    isSubmitting: boolean
}

const ProfileInfo = ({
    user, formData, onEmailChange, isEditing, isSubmitting,
}: ProfileInfoProps) => (
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
                        <StatusChip variant={isAdminRole(user?.role) ? 'warn' : 'ok'}>
                            {user?.role || USER_ROLES.USER}
                        </StatusChip>
                    </div>
                </Form.Group>
            </Col>
        </Row>

        <AuthFormField
            label="Email"
            type="email"
            name="email"
            value={formData.email}
            onChange={onEmailChange}
            placeholder="Enter your email address"
            disabled={!isEditing || isSubmitting}
        />

        <Row>
            <Col md={6}>
                <Form.Group className="mb-3">
                    <Form.Label>Account Status</Form.Label>
                    <div>
                        <StatusChip variant={user?.isActive ? 'ok' : 'err'}>
                            {user?.isActive ? 'Active' : 'Inactive'}
                        </StatusChip>
                    </div>
                </Form.Group>
            </Col>
            <Col md={6}>
                <Form.Group className="mb-3">
                    <Form.Label>Member Since</Form.Label>
                    <div className="mono text-muted small pt-1">
                        {user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : 'N/A'}
                    </div>
                </Form.Group>
            </Col>
        </Row>
    </>
)

export default ProfileInfo
