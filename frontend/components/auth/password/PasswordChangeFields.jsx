import { Form } from 'react-bootstrap'

const PasswordChangeFields = ({
    passwordData, onChange, disabled,
}) => (
    <>
        <Form.Group className="mb-3">
            <Form.Label htmlFor="currentPassword">Current Password</Form.Label>
            <Form.Control
                type="password"
                id="currentPassword"
                name="currentPassword"
                value={passwordData.currentPassword}
                onChange={onChange}
                placeholder="Enter your current password"
                disabled={disabled}
                required
            />
        </Form.Group>
        <Form.Group className="mb-3">
            <Form.Label htmlFor="newPassword">New Password</Form.Label>
            <Form.Control
                type="password"
                id="newPassword"
                name="newPassword"
                value={passwordData.newPassword}
                onChange={onChange}
                placeholder="Enter your new password"
                disabled={disabled}
                required
            />
            <Form.Text className="text-muted">
                Password must be at least 8 characters long and contain both letters and numbers.
            </Form.Text>
        </Form.Group>
        <Form.Group className="mb-3">
            <Form.Label htmlFor="confirmPassword">Confirm New Password</Form.Label>
            <Form.Control
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={passwordData.confirmPassword}
                onChange={onChange}
                placeholder="Confirm your new password"
                disabled={disabled}
                required
            />
        </Form.Group>
    </>
)

export default PasswordChangeFields
