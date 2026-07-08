'use client'
import { Card } from 'react-bootstrap'

/**
 * Tracked Streamers Card Component
 */
const TrackedStreamersCard = ({ stats }) => (
    <Card className="h-100">
        <Card.Body>
            <h3 className="section-label mb-3">Tracked streamers</h3>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Total Streamers</span>
                    <span className="mono">{stats.tracked_streamers.total}</span>
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Active</span>
                    <span className="status-chip is-ok">{stats.tracked_streamers.active}</span>
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Processing Enabled</span>
                    <span className="mono">{stats.tracked_streamers.processing_enabled}</span>
                </div>
            </div>
            <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center">
                    <span>Inactive</span>
                    <span className="status-chip">{stats.tracked_streamers.inactive}</span>
                </div>
            </div>
        </Card.Body>
    </Card>
)

export default TrackedStreamersCard
