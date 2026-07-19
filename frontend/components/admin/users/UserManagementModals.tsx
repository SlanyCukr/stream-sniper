'use client'
import {
    Modal, Button,
} from 'react-bootstrap'
import EditUserForm from './EditUserForm'
import type { AdminUser } from '@/hooks/admin/users/useUserAdminQueries'

type UserManagementDialog =
    | { type: 'edit', user: AdminUser }
    | { type: 'delete', user: AdminUser }
    | null

interface UserManagementModalsProps {
    dialog: UserManagementDialog
    onClose: () => void
    onUpdate: (user: AdminUser) => void
    onDelete: () => void
}

const UserManagementModals = ({
    dialog,
    onClose,
    onUpdate,
    onDelete,
}: UserManagementModalsProps) => (
    <>
        <Modal
            show={dialog?.type === 'edit'}
            onHide={onClose}>
            <Modal.Header closeButton>
                <Modal.Title>Edit User</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                {dialog?.type === 'edit' && (
                    <EditUserForm
                        user={dialog.user}
                        onSave={onUpdate}
                        onCancel={onClose}
                    />
                )}
            </Modal.Body>
        </Modal>

        <Modal
            show={dialog?.type === 'delete'}
            onHide={onClose}>
            <Modal.Header closeButton>
                <Modal.Title>Confirm Delete</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                Are you sure you want to delete user &quot;{dialog?.user?.username}&quot;? This action cannot be undone.
            </Modal.Body>
            <Modal.Footer>
                <Button
                    variant="outline-primary"
                    onClick={onClose}>
                    Cancel
                </Button>
                <Button
                    variant="outline-danger"
                    onClick={onDelete}>
                    <i
                        className="bi bi-trash me-2"
                        aria-hidden="true" />
                    Delete user
                </Button>
            </Modal.Footer>
        </Modal>
    </>
)

export default UserManagementModals
