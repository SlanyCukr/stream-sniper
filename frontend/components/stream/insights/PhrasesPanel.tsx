'use client'
import { useStreamPhrases } from '@/hooks/stream/insights/useStreamInsightsQuery'
import StreamInsightPanel from './StreamInsightPanel'

interface PhrasesPanelProps {
    streamId: number
}

/**
 * Recurring phrases for a stream as a chip cloud, each chip carrying its usage
 * count and a distinct-chatter tooltip. Renders an empty state until the phrase
 * rollup has run.
 */
const PhrasesPanel = ({ streamId }: PhrasesPanelProps) => {
    const query = useStreamPhrases(streamId)

    return (
        <StreamInsightPanel
            title="Recurring phrases"
            query={query}
            isEmpty={data => (data.phrases || []).length === 0}
            loadingText="Loading phrases..."
            errorTitle="Failed to load phrases"
            emptyTitle="No phrases"
            emptyHint="Phrase rollups are still pending for this stream."
        >
            {data => (
                <div
                    className="phrase-cloud"
                    role="list"
                    aria-label="Recurring phrases">
                    {(data.phrases || []).map(phrase => (
                        <span
                            key={phrase.phrase}
                            className="phrase-chip"
                            role="listitem"
                            title={`${phrase.chatterCount?.toLocaleString()} chatters`}
                            aria-label={`${phrase.phrase}: ${phrase.usageCount} uses, ${phrase.chatterCount} chatters`}>
                            <span className="phrase-text">{phrase.phrase}</span>
                            <span
                                className="phrase-count mono"
                                aria-hidden="true">
                                {phrase.usageCount?.toLocaleString()}
                            </span>
                        </span>
                    ))}
                </div>
            )}
        </StreamInsightPanel>
    )
}

export default PhrasesPanel
