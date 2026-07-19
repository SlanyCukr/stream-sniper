'use client'
import { useCallback, useState, type FormEvent } from 'react'
import type { MultiValue, SingleValue } from 'react-select'
import {
    Button, Form, Modal, Spinner,
} from 'react-bootstrap'
import AsyncSearchSelect from '@/components/common/search/AsyncSearchSelect'
import { loadTrackedStreamerOptions } from '@/hooks/admin/tracking/useTrackingQueries'
import type { CreateTrackedStreamerRequest } from '@/lib/api/tracking'
import type { SearchOption } from '@/hooks/useAsyncSearchLoader'

interface StreamerDraft {
    twitch_username: string
    notes: string
    is_active: boolean
    processing_enabled: boolean
}

const INITIAL_DRAFT: StreamerDraft = {
    twitch_username: '',
    notes: '',
    is_active: true,
    processing_enabled: true,
}

interface AddTrackedStreamerModalProps {
    show: boolean
    onHide: () => void
    // onCreate resolves to a value the caller only checks for truthiness (see
    // useActionFeedback's runAction, which always resolves to a truthy outcome
    // object regardless of success/failure).
    onCreate: (streamer: CreateTrackedStreamerRequest) => Promise<unknown>
    loadOptions?: (query: string) => Promise<SearchOption[]>
}

// AsyncSearchSelectProps (react-select's AsyncProps) doesn't declare
// formatCreateLabel — that prop belongs to the creatable variant AsyncSearchSelect
// switches to internally. Passed via spread below so it isn't excess-property
// checked against the non-creatable prop type.
const creatableSelectExtras: Record<string, unknown> = {
    formatCreateLabel: (value: string) => `Track "${value}"`,
}

const AddTrackedStreamerModal = ({
    show, onHide, onCreate, loadOptions = loadTrackedStreamerOptions,
}: AddTrackedStreamerModalProps) => {
    const [draft, setDraft] = useState<StreamerDraft>(INITIAL_DRAFT)
    const [submitting, setSubmitting] = useState(false)

    const close = useCallback(() => {
        setDraft(INITIAL_DRAFT)
        onHide()
    }, [onHide])

    const submit = async (event: FormEvent<HTMLFormElement>) => {
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
                            onChange={(newValue: SingleValue<SearchOption> | MultiValue<SearchOption>) => {
                                // isMulti isn't set on this select, so newValue is always a single
                                // option (or null) — value is a Twitch login string here.
                                const option = newValue as SingleValue<SearchOption>
                                setDraft(current => ({
                                    ...current,
                                    twitch_username: (option?.value as string | undefined) ?? '',
                                }))
                            }}
                            placeholder="Search Twitch or type a username"
                            isClearable
                            {...creatableSelectExtras} />
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
