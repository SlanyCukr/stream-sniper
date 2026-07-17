'use client'
import {
    Button, Card, Table,
} from 'react-bootstrap'
import PaginatedResultsFooter from '@/components/common/pagination/PaginatedResultsFooter'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import { formatDateTime } from '@/utils/dateUtils'

const TrackedStreamerTable = ({
    streamers,
    total,
    loading,
    pageIndex,
    pageCount,
    updatePending,
    deletePending,
    onPageChange,
    onToggleActive,
    onToggleProcessing,
    onRemove,
}) => (
    <Card>
        <Card.Body className={!loading && streamers.length === 0 ? 'p-0' : ''}>
            {loading ? (
                <LoadingSpinner text="Loading tracked streamers..." />
            ) : streamers.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-scope" aria-hidden="true" />
                    <p className="empty-title">No tracked streamers</p>
                    <p className="empty-hint">
                        No streamers match this filter. Add a streamer to start automated VOD collection.
                    </p>
                </div>
            ) : (
                <>
                    <Table hover responsive>
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>Display Name</th>
                                <th>Status</th>
                                <th>Processing</th>
                                <th>Last Check</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {streamers.map(streamer => (
                                <tr key={streamer.id}>
                                    <td><strong>{streamer.twitchUsername}</strong></td>
                                    <td>{streamer.displayName}</td>
                                    <td>
                                        <span className={`status-chip ${streamer.isActive ? 'is-ok' : 'is-err'}`}>
                                            {streamer.isActive ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`status-chip ${streamer.processingEnabled ? 'is-ok' : 'is-warn'}`}>
                                            {streamer.processingEnabled ? 'Enabled' : 'Disabled'}
                                        </span>
                                    </td>
                                    <td className="mono">{formatDateTime(streamer.lastStreamCheck, 'Never')}</td>
                                    <td className="mono">{formatDateTime(streamer.createdAt, 'Never')}</td>
                                    <td>
                                        <Button
                                            variant="outline-primary"
                                            size="sm"
                                            className="me-2"
                                            onClick={() => onToggleActive(streamer.id, streamer.isActive)}
                                            disabled={updatePending}>
                                            {streamer.isActive ? 'Deactivate' : 'Activate'}
                                        </Button>
                                        <Button
                                            variant="outline-primary"
                                            size="sm"
                                            className="me-2"
                                            onClick={() => onToggleProcessing(streamer.id, streamer.processingEnabled)}
                                            disabled={updatePending}>
                                            {streamer.processingEnabled ? 'Disable' : 'Enable'}
                                        </Button>
                                        <Button
                                            variant="outline-danger"
                                            size="sm"
                                            onClick={() => onRemove(streamer)}
                                            disabled={deletePending}>
                                            Remove
                                        </Button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                    <PaginatedResultsFooter
                        shown={streamers.length}
                        total={total}
                        pageIndex={pageIndex}
                        pageCount={pageCount}
                        onPageChange={onPageChange}
                        ariaLabel="Tracked streamers pagination"
                    />
                </>
            )}
        </Card.Body>
    </Card>
)

export default TrackedStreamerTable
