'use client'
import { useState } from 'react'
import {
    Form, Button,
} from 'react-bootstrap'

const EditUserForm = ({
    user, onSave, onCancel,
}) => {
    const [
        formData,
        setFormData,
    ] = useState({
        email: user.email,
        role: user.role,
        is_active: user.is_active,
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
            <Form.Group className="mb-3">
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
            <Form.Group className="mb-3">
                <Form.Label>Role</Form.Label>
                <Form.Select
                    value={formData.role}
                    onChange={e => setFormData({
                        ...formData,
                        role: e.target.value,
                    })}
                >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                </Form.Select>
            </Form.Group>
            <Form.Group className="mb-3">
                <Form.Check
                    type="checkbox"
                    label="Active"
                    checked={formData.is_active}
                    onChange={e => setFormData({
                        ...formData,
                        is_active: e.target.checked,
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
