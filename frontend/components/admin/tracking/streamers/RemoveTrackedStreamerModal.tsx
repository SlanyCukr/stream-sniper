'use client'
import { Button, Modal } from 'react-bootstrap'
import type { TrackedStreamer } from '@/hooks/admin/tracking/useTrackingQueries'

interface RemoveTrackedStreamerModalProps {
    target: TrackedStreamer | null
    onHide: () => void
    onConfirm: (streamerId: number | undefined) => void
}

const RemoveTrackedStreamerModal = ({ target, onHide, onConfirm }: RemoveTrackedStreamerModalProps) => (
    <Modal show={target !== null} onHide={onHide}>
        <Modal.Header closeButton>
            <Modal.Title>Remove streamer</Modal.Title>
        </Modal.Header>
        <Modal.Body>
            Are you sure you want to remove{' '}
            <strong>{target?.twitchUsername}</strong>{' '}
            from tracking?
        </Modal.Body>
        <Modal.Footer>
            <Button variant="outline-primary" onClick={onHide}>Cancel</Button>
            <Button
                variant="outline-danger"
                onClick={() => onConfirm(target?.id)}>
                Remove
            </Button>
        </Modal.Footer>
    </Modal>
)

export default RemoveTrackedStreamerModal
