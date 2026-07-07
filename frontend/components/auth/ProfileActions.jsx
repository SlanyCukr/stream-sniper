'use client'

import {
    Button, Spinner,
} from 'react-bootstrap'

/**
 * Profile Action Buttons Component
 */
const ProfileActions = ({
    isEditing,
    isSubmitting,
    loading,
    handleEditToggle,
    setShowPasswordModal,
}) => (
    <div className="d-flex gap-2">
        {isEditing ? (
            <>
                <Button
                    variant="primary"
                    type="submit"
                    disabled={isSubmitting || loading}
                >
                    {isSubmitting ? (
                        <>
                            <Spinner
                                as="span"
                                animation="border"
                                size="sm"
                                role="status"
                                aria-hidden="true"
                                className="me-2"
                            />
                            Saving...
                        </>
                    ) : (
                        'Save Changes'
                    )}
                </Button>
                <Button
                    variant="secondary"
                    onClick={handleEditToggle}
                    disabled={isSubmitting || loading}
                >
                    Cancel
                </Button>
            </>
        ) : (
            <>
                <Button
                    variant="outline-primary"
                    onClick={handleEditToggle}
                    disabled={loading}
                >
                    <i className="bi bi-pencil me-2"></i>
                    Edit Profile
                </Button>
                <Button
                    variant="outline-secondary"
                    onClick={() => setShowPasswordModal(true)}
                    disabled={loading}
                >
                    <i className="bi bi-key me-2"></i>
                    Change Password
                </Button>
            </>
        )}
    </div>
)

export default ProfileActions
