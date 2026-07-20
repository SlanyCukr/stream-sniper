'use client'

import {
    Alert, Card, Form,
} from 'react-bootstrap'
import { AuthenticationLoadingState } from '@/components/auth/guards/AuthenticatedGuard'
import { useUserProfile } from '@/hooks/auth/useUserProfile'
import ProfileInfo from './ProfileInfo'
import ProfileActions from './ProfileActions'
import PasswordChangeModal from '../password/PasswordChangeModal'

const UserProfile = () => {
    const profile = useUserProfile()

    if (profile.isInitializing) {
        return <AuthenticationLoadingState />
    }

    return (
        <Card>
            <Card.Header><h4>User Profile</h4></Card.Header>
            <Card.Body>
                {profile.error ? <Alert variant="danger" className="mb-3">{profile.error}</Alert> : null}
                {profile.success ? <Alert variant="success" className="mb-3">{profile.success}</Alert> : null}
                <Form onSubmit={profile.handleSubmit}>
                    <ProfileInfo
                        user={profile.user}
                        formData={profile.formData}
                        handleChange={profile.handleChange}
                        isEditing={profile.isEditing}
                        isSubmitting={profile.isSubmitting}
                    />
                    <div className="d-flex justify-content-end">
                        <ProfileActions
                            isEditing={profile.isEditing}
                            isSubmitting={profile.isSubmitting}
                            handleEditToggle={profile.handleEditToggle}
                            onChangePassword={profile.openPasswordModal}
                        />
                    </div>
                </Form>
            </Card.Body>
            <PasswordChangeModal
                show={profile.showPasswordModal}
                onHide={profile.closePasswordModal}
                onPasswordChange={profile.handlePasswordChange}
            />
        </Card>
    )
}

export default UserProfile
