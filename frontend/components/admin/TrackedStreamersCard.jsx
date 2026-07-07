'use client'
import {
    Card, Badge,
} from 'react-bootstrap'

/**
 * Tracked Streamers Card Component
 */
const TrackedStreamersCard = ({ stats }) => (
    <Card>
        <Card.Body>
            <h5>Tracked Streamers</h5>
            <div className="mb-3">
                <div className="d-flex justify-content-between">
                    <span>Total Streamers</span>
                    <Badge bg="primary">{stats.tracked_streamers.total}</Badge>
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between">
                    <span>Active</span>
                    <Badge bg="success">{stats.tracked_streamers.active}</Badge>
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between">
                    <span>Processing Enabled</span>
                    <Badge bg="info">{stats.tracked_streamers.processing_enabled}</Badge>
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between">
                    <span>Inactive</span>
                    <Badge bg="secondary">{stats.tracked_streamers.inactive}</Badge>
                </div>
            </div>
        </Card.Body>
    </Card>
)

export default TrackedStreamersCard
