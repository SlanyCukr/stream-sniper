'use client'
import { useCallback, useState, type FormEvent } from 'react'
import type { MultiValue, SingleValue } from 'react-select'
import {
    Button, Form, Modal, Spinner,
} from 'react-bootstrap'
import AsyncSearchSelect from '@/components/common/search/AsyncSearchSelect'
import { loadTrackedStreamerOptions } from '@/hooks/admin/tracking/useTrackingQueries'
import type { CreateTrackedStreamerCommand } from '@/lib/models/tracking'
import type { SearchOption } from '@/hooks/useAsyncSearchLoader'

interface StreamerDraft {
    twitchUsername: string
    notes: string
    isActive: boolean
    processingEnabled: boolean
}

const INITIAL_DRAFT: StreamerDraft = {
    twitchUsername: '',
    notes: '',
    isActive: true,
    processingEnabled: true,
}

interface AddTrackedStreamerModalProps {
    show: boolean
    pending?: boolean
    onHide: () => void
    onCreate: (streamer: CreateTrackedStreamerCommand) => Promise<{ ok: boolean }>
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
    show, pending = false, onHide, onCreate, loadOptions = loadTrackedStreamerOptions,
}: AddTrackedStreamerModalProps) => {
    const [draft, setDraft] = useState<StreamerDraft>(INITIAL_DRAFT)
    const [submitting, setSubmitting] = useState(false)

    const close = useCallback(() => {
        if (submitting || pending) return
        setDraft(INITIAL_DRAFT)
        onHide()
    }, [onHide, pending, submitting])

    const submit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        setSubmitting(true)
        try {
            const outcome = await onCreate(draft)
            if (outcome.ok) close()
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Modal show={show} onHide={close} backdrop={submitting || pending ? 'static' : true} keyboard={!submitting && !pending}>
            <Modal.Header closeButton={!submitting && !pending}>
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
                            value={draft.twitchUsername
                                ? { value: draft.twitchUsername, label: draft.twitchUsername }
                                : null}
                            onChange={(newValue: SingleValue<SearchOption> | MultiValue<SearchOption>) => {
                                // isMulti isn't set on this select, so newValue is always a single
                                // option (or null) — value is a Twitch login string here.
                                const option = newValue as SingleValue<SearchOption>
                                setDraft(current => ({
                                    ...current,
                                    twitchUsername: (option?.value as string | undefined) ?? '',
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
                            checked={draft.isActive}
                            onChange={event => setDraft(current => ({ ...current, isActive: event.target.checked }))} />
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Check
                            type="checkbox"
                            label="Processing Enabled"
                            checked={draft.processingEnabled}
                            onChange={event => setDraft(current => ({
                                ...current,
                                processingEnabled: event.target.checked,
                            }))} />
                    </Form.Group>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="outline-primary" onClick={close} disabled={submitting || pending}>Cancel</Button>
                    <Button
                        variant="primary"
                        type="submit"
                        disabled={submitting || pending || !draft.twitchUsername.trim()}>
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
