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
    onUpdate: (user: AdminUser) => Promise<unknown>
    onDelete: (userId: number) => Promise<unknown>
    updatePending: boolean
    deletePending: boolean
}

const UserManagementModals = ({
    dialog,
    onClose,
    onUpdate,
    onDelete,
    updatePending,
    deletePending,
}: UserManagementModalsProps) => (
    <>
        {dialog?.type === 'edit' ? (
            <Modal
                show
                onHide={() => {
                    if (!updatePending) onClose()
                }}>
                <Modal.Header closeButton={!updatePending}>
                    <Modal.Title>Edit User</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <EditUserForm
                        user={dialog.user}
                        onSave={onUpdate}
                        onCancel={onClose}
                        isPending={updatePending}
                    />
                </Modal.Body>
            </Modal>
        ) : null}

        {dialog?.type === 'delete' ? (
            <Modal
                show
                onHide={() => {
                    if (!deletePending) onClose()
                }}>
                <Modal.Header closeButton={!deletePending}>
                    <Modal.Title>Confirm Delete</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    Are you sure you want to delete user &quot;{dialog.user.username}&quot;? This action cannot be undone.
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        variant="outline-primary"
                        onClick={onClose}
                        disabled={deletePending}>
                        Cancel
                    </Button>
                    <Button
                        variant="outline-danger"
                        onClick={() => void onDelete(dialog.user.id)}
                        disabled={deletePending}>
                        <i
                            className="bi bi-trash me-2"
                            aria-hidden="true" />
                        Delete user
                    </Button>
                </Modal.Footer>
            </Modal>
        ) : null}
    </>
)

export default UserManagementModals
