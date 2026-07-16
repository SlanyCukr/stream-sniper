'use client'
import { useCallback, useState } from 'react'
import {
    Button, Form, Modal, Spinner,
} from 'react-bootstrap'
import AsyncSearchSelect from '@/components/common/search/AsyncSearchSelect'
import { loadTrackedStreamerOptions } from '@/hooks/admin/tracking/useTrackingQueries'

const INITIAL_DRAFT = {
    twitch_username: '',
    notes: '',
    is_active: true,
    processing_enabled: true,
}

const AddTrackedStreamerModal = ({
    show, onHide, onCreate, loadOptions = loadTrackedStreamerOptions,
}) => {
    const [draft, setDraft] = useState(INITIAL_DRAFT)
    const [submitting, setSubmitting] = useState(false)

    const close = useCallback(() => {
        setDraft(INITIAL_DRAFT)
        onHide()
    }, [onHide])

    const submit = async event => {
        event.preventDefault()
        setSubmitting(true)
        try {
            const created = await onCreate(draft)
            if (created) close()
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Modal show={show} onHide={close}>
            <Modal.Header closeButton>
                <Modal.Title>Add Streamer to Tracking</Modal.Title>
            </Modal.Header>
            <Form onSubmit={submit}>
                <Modal.Body>
                    <Form.Group className="mb-3">
                        <Form.Label htmlFor="add-streamer-username">Twitch Username *</Form.Label>
                        <AsyncSearchSelect
                            creatable
                            instanceId="add-streamer-username-select"
                            inputId="add-streamer-username"
                            loadOptions={loadOptions}
                            value={draft.twitch_username
                                ? { value: draft.twitch_username, label: draft.twitch_username }
                                : null}
                            onChange={option => setDraft(current => ({
                                ...current,
                                twitch_username: option?.value ?? '',
                            }))}
                            placeholder="Search Twitch or type a username"
                            formatCreateLabel={value => `Track "${value}"`}
                            isClearable />
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Label>Notes</Form.Label>
                        <Form.Control
                            as="textarea"
                            rows={3}
                            value={draft.notes}
                            onChange={event => setDraft(current => ({ ...current, notes: event.target.value }))}
                            placeholder="Optional notes about this streamer" />
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Check
                            type="checkbox"
                            label="Active"
                            checked={draft.is_active}
                            onChange={event => setDraft(current => ({ ...current, is_active: event.target.checked }))} />
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Check
                            type="checkbox"
                            label="Processing Enabled"
                            checked={draft.processing_enabled}
                            onChange={event => setDraft(current => ({
                                ...current,
                                processing_enabled: event.target.checked,
                            }))} />
                    </Form.Group>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="outline-primary" onClick={close}>Cancel</Button>
                    <Button
                        variant="primary"
                        type="submit"
                        disabled={submitting || !draft.twitch_username.trim()}>
                        {submitting ? (
                            <><Spinner animation="border" size="sm" className="me-2" />Adding...</>
                        ) : 'Add Streamer'}
                    </Button>
                </Modal.Footer>
            </Form>
        </Modal>
    )
}

export default AddTrackedStreamerModal
