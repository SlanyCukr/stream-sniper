'use client'
import {
    Button, Card, Table,
} from 'react-bootstrap'
import PaginatedResultsFooter from '@/components/common/pagination/PaginatedResultsFooter'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import StatusChip from '@/components/common/StatusChip'
import { formatDateTime } from '@/utils/dateUtils'

/**
 * Dormant-vs-broken triage cell: what an on-demand Twitch probe said about the
 * channel, next to what the collector has actually ingested. No probe yet →
 * just the button.
 */
const TwitchProbeCell = ({
    streamer, result, probing, onProbe,
}) => (
    <div className="d-flex align-items-center gap-2 flex-wrap">
        {result && (
            result.isLive ? (
                <StatusChip variant="ok">Live now</StatusChip>
            ) : result.archiveVodCount === 0 ? (
                <StatusChip variant="warn">No VODs</StatusChip>
            ) : (
                <span className="mono" title={`${result.archiveVodCount} archive VODs`}>
                    Last VOD {formatDateTime(result.lastVodCreatedAt, 'unknown')}
                </span>
            )
        )}
        <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => onProbe(streamer.id)}
            disabled={probing}>
            {probing ? 'Probing…' : result ? 'Re-probe' : 'Probe Twitch'}
        </Button>
    </div>
)

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
    onProbe,
    probeResults = {},
    probingId = null,
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
                                <th>Collected</th>
                                <th>Last Check</th>
                                <th>Twitch</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {streamers.map(streamer => (
                                <tr key={streamer.id}>
                                    <td><strong>{streamer.twitchUsername}</strong></td>
                                    <td>{streamer.displayName}</td>
                                    <td>
                                        <StatusChip variant={streamer.isActive ? 'ok' : 'err'}>
                                            {streamer.isActive ? 'Active' : 'Inactive'}
                                        </StatusChip>
                                    </td>
                                    <td>
                                        <StatusChip variant={streamer.processingEnabled ? 'ok' : 'warn'}>
                                            {streamer.processingEnabled ? 'Enabled' : 'Disabled'}
                                        </StatusChip>
                                    </td>
                                    <td className="mono">
                                        {streamer.totalStreamsCollected
                                            ? `${streamer.totalStreamsCollected} · ${formatDateTime(streamer.lastCollectedStreamStart, 'unknown')}`
                                            : 'Nothing yet'}
                                    </td>
                                    <td className="mono">{formatDateTime(streamer.lastStreamCheck, 'Never')}</td>
                                    <td>
                                        <TwitchProbeCell
                                            streamer={streamer}
                                            result={probeResults[streamer.id]}
                                            probing={probingId === streamer.id}
                                            onProbe={onProbe}
                                        />
                                    </td>
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
