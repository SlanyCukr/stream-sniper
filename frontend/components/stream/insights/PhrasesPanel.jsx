'use client'
import { Card } from 'react-bootstrap'
import { useStreamPhrases } from '@/hooks/stream/insights/useStreamInsightsQuery'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'

/**
 * Recurring phrases for a stream as a chip cloud, each chip carrying its usage
 * count and a distinct-chatter tooltip. Renders an empty state until the phrase
 * rollup has run.
 *
 * @param {object} props
 * @param {number} props.streamId
 */
const PhrasesPanel = ({ streamId }) => {
    const {
        data,
        isLoading,
        error,
        refetch,
    } = useStreamPhrases(streamId)

    const phrases = data?.phrases || []

    return (
        <Card className="insight-panel">
            <Card.Body>
                <h3 className="section-label mb-3">Recurring phrases</h3>

                {isLoading && (
                    <LoadingSpinner
                        size="md"
                        text="Loading phrases..."
                    />
                )}

                {error && !isLoading && (
                    <ErrorAlert
                        error={error}
                        title="Failed to load phrases"
                        onRetry={refetch}
                        showDetails={process.env.NODE_ENV === 'development'}
                    />
                )}

                {!isLoading && !error && phrases.length === 0 && (
                    <div className="empty-state">
                        <div
                            className="empty-scope"
                            aria-hidden="true" />
                        <p className="empty-title">No phrases</p>
                        <p className="empty-hint">
                            Phrase rollups are still pending for this stream.
                        </p>
                    </div>
                )}

                {!isLoading && !error && phrases.length > 0 && (
                    <div
                        className="phrase-cloud"
                        role="list"
                        aria-label="Recurring phrases">
                        {phrases.map(phrase => (
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
            </Card.Body>
        </Card>
    )
}

export default PhrasesPanel
