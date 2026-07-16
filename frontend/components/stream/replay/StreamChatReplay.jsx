'use client'

import { useCallback } from 'react'
import { Virtuoso } from 'react-virtuoso'
import { useChatReplayNavigation } from '@/hooks/stream/replay/useChatReplayNavigation'
import ChatReplayLine from './ChatReplayLine'

const StreamChatReplay = ({
    messages,
    hasMore,
    isFetchingMore,
    onLoadMore,
    jumpToTs,
}) => {
    const {
        virtuosoRef, flashId, handleEndReached,
    } = useChatReplayNavigation({
        messages,
        jumpToTs,
        hasMore,
        isFetchingMore,
        onLoadMore,
    })
    const renderRow = useCallback((index, message) => (
        <ChatReplayLine message={message} isFlashing={message.id === flashId} />
    ), [flashId])
    const renderFooter = useCallback(() => (
        isFetchingMore ? <div className="chat-replay-footer">Loading more messages…</div> : null
    ), [isFetchingMore])

    return (
        <div className="chat-panel" role="log" aria-live="polite" aria-label="Stream chat replay" tabIndex="0">
            <div className="chat-panel-head" aria-hidden="true">
                <i className="bi bi-chat-left-text" />
                <span>Chat replay</span>
                <span className="chat-count">{messages.length.toLocaleString()} loaded</span>
            </div>
            {messages.length > 0 ? (
                <div className="chat-panel-body chat-panel-body--replay">
                    <Virtuoso
                        ref={virtuosoRef}
                        data={messages}
                        itemContent={renderRow}
                        endReached={handleEndReached}
                        components={{ Footer: renderFooter }}
                        style={{ height: '520px' }}
                    />
                </div>
            ) : (
                <p className="text-muted small mb-0 px-3 py-3">No messages match these filters.</p>
            )}
        </div>
    )
}

export default StreamChatReplay
