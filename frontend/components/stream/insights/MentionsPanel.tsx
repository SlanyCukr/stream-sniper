'use client'
import { useStreamMentions } from '@/hooks/stream/insights/useStreamInsightsQuery'
import StreamInsightPanel from './StreamInsightPanel'

interface MentionsPanelProps {
    streamId: number
}

/**
 * Most-mentioned chatters for a stream, with a compact "top exchanges" sub-list.
 * Reads the mentions rollup; renders an empty state (not fake zeros) until the
 * rollup has run. Nicks are plain text — the chatter explorer has no deep-link
 * to preselect a target — matching the existing StreamStatsCard rank list.
 */
const MentionsPanel = ({ streamId }: MentionsPanelProps) => {
    const query = useStreamMentions(streamId)
    const mentioned = query.data?.mentioned || []
    const pairs = query.data?.pairs || []
    const maxCount = Math.max(1, ...mentioned.map(m => m.count || 0))

    return (
        <StreamInsightPanel
            title="Most mentioned"
            query={query}
            hasItems={mentioned.length > 0}
            loadingText="Loading mentions..."
            errorTitle="Failed to load mentions"
            emptyTitle="No mentions"
            emptyHint="Mention rollups are still pending for this stream."
        >
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
        </StreamInsightPanel>
    )
}

export default MentionsPanel
