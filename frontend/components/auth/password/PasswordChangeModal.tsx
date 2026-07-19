'use client'

import {
    Alert, Button, Form, Modal, Spinner,
} from 'react-bootstrap'
import { usePasswordChangeForm } from '@/hooks/auth/usePasswordChangeForm'
import type { PasswordChangeData } from '@/utils/validationUtils'
import PasswordChangeFields from './PasswordChangeFields'

interface PasswordChangeModalProps {
    show: boolean
    onHide: () => void
    onPasswordChange: (passwordData: PasswordChangeData) => Promise<unknown>
}

const PasswordChangeModal = ({
    show, onHide, onPasswordChange,
}: PasswordChangeModalProps) => {
    const form = usePasswordChangeForm({
        onPasswordChange,
        onHide,
    })
    const disabled = form.isSubmitting

    return (
        <Modal show={show} onHide={form.handleClose} backdrop="static">
            <Modal.Header closeButton><Modal.Title>Change Password</Modal.Title></Modal.Header>
            <Form onSubmit={form.handleSubmit}>
                <Modal.Body>
                    {form.error ? <Alert variant="danger" className="mb-3">{form.error}</Alert> : null}
                    <PasswordChangeFields
                        passwordData={form.passwordData}
                        onChange={form.handleChange}
                        disabled={disabled}
                    />
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="outline-primary" onClick={form.handleClose} disabled={disabled}>
                        Cancel
                    </Button>
                    <Button variant="primary" type="submit" disabled={disabled}>
                        {form.isSubmitting ? (
                            <>
                                <Spinner
                                    as="span"
                                    animation="border"
                                    size="sm"
                                    role="status"
                                    aria-hidden="true"
                                    className="me-2"
                                />
                                Changing Password...
                            </>
                        ) : 'Change Password'}
                    </Button>
                </Modal.Footer>
            </Form>
        </Modal>
    )
}

export default PasswordChangeModal
