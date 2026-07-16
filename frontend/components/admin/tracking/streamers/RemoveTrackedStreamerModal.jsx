'use client'
import { Button, Modal } from 'react-bootstrap'

const RemoveTrackedStreamerModal = ({ target, onHide, onConfirm }) => (
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
