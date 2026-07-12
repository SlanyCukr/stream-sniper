'use client'
import { Card } from 'react-bootstrap'
import { useStreamMentions } from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

/**
 * Most-mentioned chatters for a stream, with a compact "top exchanges" sub-list.
 * Reads the mentions rollup; renders an empty state (not fake zeros) until the
 * rollup has run. Nicks are plain text — the chatter explorer has no deep-link
 * to preselect a target — matching the existing StreamStatsCard rank list.
 *
 * @param {object} props
 * @param {number} props.streamId
 */
const MentionsPanel = ({ streamId }) => {
    const {
        data,
        isLoading,
        error,
        refetch,
    } = useStreamMentions(streamId)

    const mentioned = data?.mentioned || []
    const pairs = data?.pairs || []
    const maxCount = Math.max(1, ...mentioned.map(m => m.count || 0))

    return (
        <Card className="insight-panel">
            <Card.Body>
                <h3 className="section-label mb-3">Most mentioned</h3>

                {isLoading && (
                    <LoadingSpinner
                        size="md"
                        text="Loading mentions..."
                    />
                )}

                {error && !isLoading && (
                    <ErrorAlert
                        error={error}
                        title="Failed to load mentions"
                        onRetry={refetch}
                        showDetails={process.env.NODE_ENV === 'development'}
                    />
                )}

                {!isLoading && !error && mentioned.length === 0 && (
                    <div className="empty-state">
                        <div
                            className="empty-scope"
                            aria-hidden="true" />
                        <p className="empty-title">No mentions</p>
                        <p className="empty-hint">
                            Mention rollups are still pending for this stream.
                        </p>
                    </div>
                )}

                {!isLoading && !error && mentioned.length > 0 && (
                    <>
                        <ul
                            className="rank-list mention-list"
                            role="list"
                            aria-label="Most mentioned chatters">
                            {mentioned.map((mention, index) => (
                                <li
                                    key={mention.chatterId}
                                    aria-label={`Rank ${index + 1}: ${mention.nick}, mentioned ${mention.count} times`}>
                                    <span
                                        className="rank"
                                        aria-hidden="true">
                                        {String(index + 1).padStart(2, '0')}
                                    </span>
                                    <div className="mention-body">
                                        <div className="mention-row">
                                            <span className="nick">{mention.nick}</span>
                                            <span
                                                className="count mono"
                                                aria-hidden="true">
                                                {mention.count?.toLocaleString()}
                                            </span>
                                        </div>
                                        <span
                                            className="data-bar"
                                            aria-hidden="true">
                                            <span
                                                className="data-bar-fill"
                                                style={{ width: `${((mention.count || 0) / maxCount) * 100}%` }}
                                            />
                                        </span>
                                    </div>
                                </li>
                            ))}
                        </ul>

                        {pairs.length > 0 && (
                            <div className="mention-pairs">
                                <h4 className="section-label mb-2">Top exchanges</h4>
                                <ul
                                    className="pair-list"
                                    role="list"
                                    aria-label="Top mention exchanges">
                                    {pairs.map(pair => (
                                        <li key={`${pair.fromChatterId}-${pair.toChatterId}`}>
                                            <span className="pair-names">
                                                {pair.fromNick}
                                                <span
                                                    className="pair-arrow"
                                                    aria-hidden="true"> → </span>
                                                {pair.toNick}
                                            </span>
                                            <span
                                                className="pair-count mono"
                                                aria-hidden="true">
                                                ×{pair.count?.toLocaleString()}
                                            </span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </>
                )}
            </Card.Body>
        </Card>
    )
}

export default MentionsPanel
