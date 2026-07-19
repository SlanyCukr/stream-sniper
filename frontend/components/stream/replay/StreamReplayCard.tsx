'use client'
import { Card } from 'react-bootstrap'
import type { JumpTarget } from '@/hooks/stream/replay/useChatReplayNavigation'
import type { StreamMessage } from '@/hooks/stream/replay/useStreamMessagesQuery'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import StreamChatReplay from './StreamChatReplay'
import StreamReplayFilters, { type ChatterOption } from './StreamReplayFilters'

interface StreamReplayCardProps {
    chatterOptions: ChatterOption[]
    replay: {
        filterCommands: {
            onChatterChange: (chatterId: number | undefined) => void
            onQueryChange: (query: string | undefined) => void
            onSubOnlyChange: (subOnly: boolean) => void
        }
        messagePage: {
            messages: StreamMessage[]
            hasMore: boolean
            isFetchingMore: boolean
            onLoadMore: () => void
        }
        queryState: {
            isLoading: boolean
            error: Error | null
        }
        navigation: {
            jumpToTs: JumpTarget | null
        }
    }
}

/**
 * Stream chat replay coordinator. The parent owns server-side query state;
 * StreamReplayFilters owns filter drafts and StreamChatReplay owns the
 * virtualized message list.
 */
const StreamReplayCard = ({
    chatterOptions,
    replay,
}: StreamReplayCardProps) => {
    const { filterCommands, messagePage, queryState, navigation } = replay
    return (
        <Card>
            <Card.Body>
                <h2 className="section-label mb-1" id="chat-replay-heading">Chat replay</h2>
                <p className="text-muted small mb-3">
                    {chatterOptions.length.toLocaleString()} chatters recorded — filter by chatter or search the text.
                </p>

                <StreamReplayFilters
                    chatterOptions={chatterOptions}
                    onChatterChange={filterCommands.onChatterChange}
                    onQueryChange={filterCommands.onQueryChange}
                    onSubOnlyChange={filterCommands.onSubOnlyChange}
                />

                {queryState.error ? (
                    <ErrorAlert error={queryState.error} title="Failed to load messages" className="mt-3" />
                ) : null}
                {queryState.isLoading && !queryState.error ? (
                    <LoadingSpinner text="Loading messages..." className="mt-3" />
                ) : !queryState.error ? (
                    <StreamChatReplay
                        messages={messagePage.messages}
                        hasMore={messagePage.hasMore}
                        isFetchingMore={messagePage.isFetchingMore}
                        onLoadMore={messagePage.onLoadMore}
                        jumpToTs={navigation.jumpToTs}
                    />
                ) : null}
            </Card.Body>
        </Card>
    )
}

export default StreamReplayCard
