'use client'
import { Button, Modal } from 'react-bootstrap'
import type { TrackedStreamer } from '@/hooks/admin/tracking/useTrackingQueries'

interface RemoveTrackedStreamerModalProps {
    target: TrackedStreamer | null
    pending: boolean
    onHide: () => void
    onConfirm: (streamerId: number) => Promise<unknown>
}

const RemoveTrackedStreamerModal = ({
    target, pending, onHide, onConfirm,
}: RemoveTrackedStreamerModalProps) => {
    const confirm = async () => {
        if (target) await onConfirm(target.id)
    }

    return (
      <Modal show={target !== null} onHide={pending ? undefined : onHide}>
        <Modal.Header closeButton={!pending}>
            <Modal.Title>Remove streamer</Modal.Title>
        </Modal.Header>
        <Modal.Body>
            Are you sure you want to remove{' '}
            <strong>{target?.twitchUsername}</strong>{' '}
            from tracking?
        </Modal.Body>
        <Modal.Footer>
            <Button variant="outline-primary" onClick={onHide} disabled={pending}>Cancel</Button>
            <Button
                variant="outline-danger"
                disabled={target === null || pending}
                onClick={confirm}>
                {pending ? 'Removing…' : 'Remove'}
            </Button>
        </Modal.Footer>
      </Modal>
    )
}

export default RemoveTrackedStreamerModal
