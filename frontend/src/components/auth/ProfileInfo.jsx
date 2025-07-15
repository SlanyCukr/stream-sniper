import {
    Form, Row, Col, Badge,
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
                        className="bg-light"
                    />
                    <small className="text-muted">Username cannot be changed</small>
                </Form.Group>
            </Col>
            <Col md={6}>
                <Form.Group className="mb-3">
                    <Form.Label>Role</Form.Label>
                    <div>
                        <Badge
                            variant={user?.role === 'admin' ? 'danger' : 'primary'}
                            className="fs-6"
                        >
                            {user?.role || 'user'}
                        </Badge>
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

        <Form.Group className="mb-3">
            <Form.Label>Account Status</Form.Label>
            <div>
                <Badge variant={user?.is_active ? 'success' : 'warning'}>
                    {user?.is_active ? 'Active' : 'Inactive'}
                </Badge>
            </div>
        </Form.Group>

        <Form.Group className="mb-3">
            <Form.Label>Member Since</Form.Label>
            <div className="text-muted">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
            </div>
        </Form.Group>
    </>
)

export default ProfileInfo
