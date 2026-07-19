'use client'

import {
    Button, Spinner,
} from 'react-bootstrap'

interface ProfileActionsProps {
    isEditing: boolean
    isSubmitting: boolean
    handleEditToggle: () => void
    onChangePassword: () => void
}

const ProfileActions = ({
    isEditing,
    isSubmitting,
    handleEditToggle,
    onChangePassword,
}: ProfileActionsProps) => (
    <div className="d-flex gap-2">
        {isEditing ? (
            <>
                <Button
                    variant="primary"
                    type="submit"
                    disabled={isSubmitting}
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
                    disabled={isSubmitting}
                >
                    Cancel
                </Button>
            </>
        ) : (
            <>
                <Button
                    variant="outline-primary"
                    onClick={handleEditToggle}
                >
                    <i className="bi bi-pencil me-2"></i>
                    Edit Profile
                </Button>
                <Button
                    variant="outline-secondary"
                    onClick={onChangePassword}
                >
                    <i className="bi bi-key me-2"></i>
                    Change Password
                </Button>
            </>
        )}
    </div>
)

export default ProfileActions
