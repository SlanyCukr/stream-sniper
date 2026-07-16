'use client'
import { useStreamEmotes } from '@/hooks/stream/insights/useStreamInsightsQuery'
import StreamInsightPanel from './StreamInsightPanel'

// provider_id becomes a CDN URL path segment — only trust the safe id charset.
const PROVIDER_ID_RE = /^[A-Za-z0-9_-]{1,64}$/

/**
 * Resolve a CDN image URL for an emote, or null (name-only cell) when the
 * provider id is missing or does not match the safe id charset.
 * @param {{source: string, providerId?: string}} emote
 * @returns {string|null}
 */
const emoteImageSrc = emote => {
    if (!emote.providerId || !PROVIDER_ID_RE.test(emote.providerId)) {
        return null
    }
    if (emote.source === 'bttv') {
        return `https://cdn.betterttv.net/emote/${emote.providerId}/1x`
    }
    if (emote.source === 'twitch') {
        return `https://static-cdn.jtvnw.net/emoticons/v2/${emote.providerId}/default/dark/1.0`
    }
    return null
}

/**
 * Emote usage for a stream: a grid of emote cells (CDN image when the provider
 * id is safe, else a name-only monogram) with usage + distinct-chatter counts.
 * Renders an empty state until the emote rollup has run.
 *
 * @param {object} props
 * @param {number} props.streamId
 */
const EmotesPanel = ({ streamId }) => {
    const query = useStreamEmotes(streamId)
    const emotes = query.data?.emotes || []

    return (
        <StreamInsightPanel
            title="Top emotes"
            query={query}
            hasItems={emotes.length > 0}
            loadingText="Loading emotes..."
            errorTitle="Failed to load emotes"
            emptyTitle="No emotes"
            emptyHint="Emote rollups are still pending for this stream."
        >
                    <ul
                        className="emote-grid"
                        role="list"
                        aria-label="Top emotes">
                        {emotes.map(emote => {
                            const src = emoteImageSrc(emote)
                            return (
                                <li
                                    key={`${emote.source}:${emote.name}`}
                                    className="emote-cell"
                                    aria-label={`${emote.name}: ${emote.usageCount} uses, ${emote.chatterCount} chatters`}>
                                    <span className="emote-thumb">
                                        {src
                                            ? (
                                                // eslint-disable-next-line @next/next/no-img-element
                                                <img
                                                    src={src}
                                                    alt={emote.name}
                                                    loading="lazy"
                                                />
                                            )
                                            : (
                                                <span
                                                    className="emote-monogram"
                                                    aria-hidden="true">
                                                    {emote.name.slice(0, 2)}
                                                </span>
                                            )}
                                    </span>
                                    <span
                                        className="emote-name"
                                        title={emote.name}>
                                        {emote.name}
                                    </span>
                                    <span
                                        className="emote-counts"
                                        aria-hidden="true">
                                        <span
                                            className="mono"
                                            title="Total uses">
                                            {emote.usageCount?.toLocaleString()}
                                        </span>
                                        <span
                                            className="emote-chatters"
                                            title="Distinct chatters">
                                            {emote.chatterCount?.toLocaleString()} chatters
                                        </span>
                                    </span>
                                </li>
                            )
                        })}
                    </ul>
        </StreamInsightPanel>
    )
}

export default EmotesPanel
