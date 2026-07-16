'use client'
import { useState } from 'react'
import {
    Form, Button,
} from 'react-bootstrap'
import { USER_ROLE_OPTIONS } from '@/lib/auth/roles'

const EditUserForm = ({
    user, onSave, onCancel,
}) => {
    const [
        formData,
        setFormData,
    ] = useState({
        email: user.email,
        role: user.role,
        isActive: user.isActive,
    })

    const handleSubmit = e => {
        e.preventDefault()
        onSave({
            ...user,
            ...formData,
        })
    }

    return (
        <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3" controlId="edit-user-email">
                <Form.Label>Email</Form.Label>
                <Form.Control
                    type="email"
                    value={formData.email}
                    onChange={e => setFormData({
                        ...formData,
                        email: e.target.value,
                    })}
                    required
                />
            </Form.Group>
            <Form.Group className="mb-3" controlId="edit-user-role">
                <Form.Label>Role</Form.Label>
                <Form.Select
                    value={formData.role}
                    onChange={e => setFormData({
                        ...formData,
                        role: e.target.value,
                    })}
                >
                    {USER_ROLE_OPTIONS.map(option => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                </Form.Select>
            </Form.Group>
            <Form.Group className="mb-3" controlId="edit-user-active">
                <Form.Check
                    type="checkbox"
                    label="Active"
                    checked={formData.isActive}
                    onChange={e => setFormData({
                        ...formData,
                        isActive: e.target.checked,
                    })}
                />
            </Form.Group>
            <div className="d-flex justify-content-end">
                <Button
                    variant="outline-primary"
                    onClick={onCancel}
                    className="me-2">
                    Cancel
                </Button>
                <Button
                    variant="primary"
                    type="submit">
                    Save Changes
                </Button>
            </div>
        </Form>
    )
}

export default EditUserForm
