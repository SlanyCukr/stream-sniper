'use client'
import type { ChangeEvent } from 'react'
import {
    Alert, Button, Form, Spinner,
} from 'react-bootstrap'
import { useCreateUserForm } from '@/hooks/admin/users/useCreateUserForm'
import ActionFeedback from '@/components/admin/ActionFeedback'
import { USER_ROLE_OPTIONS } from '@/lib/auth/roles'

const CreateUserForm = () => {
    const {
        formData,
        validationError,
        feedback,
        loading,
        handleInputChange,
        handleSubmit,
        dismissValidationError,
        cancel,
    } = useCreateUserForm()

    // useCreateUserForm types handleInputChange for HTMLInputElement only; it reads
    // target.name/value/type/checked, all of which also exist on a select change
    // event, so this reuses the same handler for the role <Form.Select>.
    const handleRoleChange = handleInputChange as unknown as (event: ChangeEvent<HTMLSelectElement>) => void

    return (
        <>
            {validationError ? (
                <Alert variant="warning" dismissible onClose={dismissValidationError}>
                    {validationError}
                </Alert>
            ) : null}
            <ActionFeedback feedback={feedback} />

            <Form onSubmit={handleSubmit}>
                <Form.Group className="mb-3" controlId="create-user-username">
                    <Form.Label>Username *</Form.Label>
                    <Form.Control
                        type="text"
                        name="username"
                        value={formData.username}
                        onChange={handleInputChange}
                        placeholder="Enter username"
                        required
                        minLength={3}
                        maxLength={50}
                    />
                    <Form.Text className="text-muted">
                        3-50 characters, letters, numbers, hyphens, and underscores only
                    </Form.Text>
                </Form.Group>

                <Form.Group className="mb-3" controlId="create-user-email">
                    <Form.Label>Email *</Form.Label>
                    <Form.Control
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleInputChange}
                        placeholder="Enter email address"
                        required
                    />
                </Form.Group>

                <Form.Group className="mb-3" controlId="create-user-password">
                    <Form.Label>Password *</Form.Label>
                    <Form.Control
                        type="password"
                        name="password"
                        value={formData.password}
                        onChange={handleInputChange}
                        placeholder="Enter password"
                        required
                        minLength={8}
                    />
                    <Form.Text className="text-muted">
                        At least 8 characters with letters and numbers
                    </Form.Text>
                </Form.Group>

                <Form.Group className="mb-3" controlId="create-user-confirm-password">
                    <Form.Label>Confirm Password *</Form.Label>
                    <Form.Control
                        type="password"
                        name="confirmPassword"
                        value={formData.confirmPassword}
                        onChange={handleInputChange}
                        placeholder="Confirm password"
                        required
                    />
                </Form.Group>

                <Form.Group className="mb-3" controlId="create-user-role">
                    <Form.Label>Role</Form.Label>
                    <Form.Select name="role" value={formData.role} onChange={handleRoleChange}>
                        {USER_ROLE_OPTIONS.map(option => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                    </Form.Select>
                </Form.Group>

                <Form.Group className="mb-3">
                    <Form.Check
                        type="checkbox"
                        name="is_active"
                        checked={formData.is_active}
                        onChange={handleInputChange}
                        label="Active User"
                    />
                    <Form.Text className="text-muted">Inactive users cannot log in</Form.Text>
                </Form.Group>

                <div className="d-grid gap-2">
                    <Button variant="primary" type="submit" disabled={loading}>
                        {loading ? (
                            <><Spinner animation="border" size="sm" className="me-2" />Creating User...</>
                        ) : (
                            <><i className="bi bi-person-plus me-2" aria-hidden="true" />Create user</>
                        )}
                    </Button>
                    <Button variant="outline-primary" onClick={cancel} disabled={loading}>Cancel</Button>
                </div>
            </Form>
        </>
    )
}

export default CreateUserForm
