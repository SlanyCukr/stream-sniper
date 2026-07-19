'use client'
import { useState, type FormEvent } from 'react'
import {
    Form, Button,
} from 'react-bootstrap'
import { USER_ROLE_OPTIONS, type UserRole } from '@/lib/auth/roles'
import type { AdminUser } from '@/hooks/admin/users/useUserAdminQueries'

interface EditUserFormProps {
    user: AdminUser
    onSave: (user: AdminUser) => void
    onCancel: () => void
}

interface EditUserFormData {
    email: string
    role: UserRole
    isActive: boolean
}

const EditUserForm = ({
    user, onSave, onCancel,
}: EditUserFormProps) => {
    const [
        formData,
        setFormData,
    ] = useState<EditUserFormData>({
        email: user.email,
        role: user.role,
        isActive: user.isActive,
    })

    const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
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
                        // select options are rendered from USER_ROLE_OPTIONS, so the raw
                        // string value is always a UserRole; the DOM API can't express that.
                        role: e.target.value as UserRole,
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
