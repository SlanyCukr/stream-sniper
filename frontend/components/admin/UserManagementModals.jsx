'use client'
import {
    Modal, Button,
} from 'react-bootstrap'
import EditUserForm from './EditUserForm'

const UserManagementModals = ({
    showEditModal,
    setShowEditModal,
    showDeleteModal,
    setShowDeleteModal,
    selectedUser,
    handleUserUpdate,
    handleUserDelete,
}) => (
    <>
        {/* Edit User Modal */}
        <Modal
            show={showEditModal}
            onHide={() => setShowEditModal(false)}>
            <Modal.Header closeButton>
                <Modal.Title>Edit User</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                {selectedUser && (
                    <EditUserForm
                        user={selectedUser}
                        onSave={handleUserUpdate}
                        onCancel={() => setShowEditModal(false)}
                    />
                )}
            </Modal.Body>
        </Modal>

        {/* Delete Confirmation Modal */}
        <Modal
            show={showDeleteModal}
            onHide={() => setShowDeleteModal(false)}>
            <Modal.Header closeButton>
                <Modal.Title>Confirm Delete</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                Are you sure you want to delete user "{selectedUser?.username}"? This action cannot be undone.
            </Modal.Body>
            <Modal.Footer>
                <Button
                    variant="outline-primary"
                    onClick={() => setShowDeleteModal(false)}>
                    Cancel
                </Button>
                <Button
                    variant="outline-danger"
                    onClick={handleUserDelete}>
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
