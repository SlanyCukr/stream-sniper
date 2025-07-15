import PropTypes from 'prop-types'
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
                    variant="secondary"
                    onClick={() => setShowDeleteModal(false)}>
                    Cancel
                </Button>
                <Button
                    variant="danger"
                    onClick={handleUserDelete}>
                    Delete User
                </Button>
            </Modal.Footer>
        </Modal>
    </>
)

UserManagementModals.propTypes = {
    showEditModal: PropTypes.bool.isRequired,
    setShowEditModal: PropTypes.func.isRequired,
    showDeleteModal: PropTypes.bool.isRequired,
    setShowDeleteModal: PropTypes.func.isRequired,
    selectedUser: PropTypes.shape({
        id: PropTypes.number,
        username: PropTypes.string,
        email: PropTypes.string,
        role: PropTypes.string,
        is_active: PropTypes.bool,
    }),
    handleUserUpdate: PropTypes.func.isRequired,
    handleUserDelete: PropTypes.func.isRequired,
}

export default UserManagementModals
