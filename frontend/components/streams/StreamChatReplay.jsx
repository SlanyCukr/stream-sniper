'use client'
import {
    useCallback,
    useEffect,
    useRef,
    useState,
} from 'react'
import { Virtuoso } from 'react-virtuoso'
import {
    applyBetterTvEmotes,
    nickColor,
    parseBadges,
} from '@/utils/chatRender'

/**
 * Extracts an HH:mm:ss clock from an ISO-ish timestamp string
 * ("YYYY-MM-DDTHH:MM:SS" -> "HH:MM:SS"). String slicing avoids a Date parse
 * (and the timezone shift that would come with it) for every rendered row.
 * @param {string} ts
 * @returns {string}
 */
const clockFromTs = ts => {
    if (!ts) {
        return ''
    }
    const timePart = String(ts).split('T')[1] || ''
    return timePart.slice(0, 8)
}

/**
 * Full chronological chat replay for a stream. Virtualizes the flattened
 * infinite-query pages so only visible rows hit the DOM; `endReached` pulls the
 * next keyset page. When `jumpToTs` changes it scrolls to the first row at or
 * after the target timestamp and briefly flashes it.
 * @param {object} props
 * @param {Array} props.messages           Flattened rows: {id, ts, chatterId, nick, text}
 * @param {boolean} props.hasMore          Whether another page can be fetched
 * @param {boolean} props.isFetchingMore   A page fetch is in flight
 * @param {Function} props.onLoadMore      Requests the next page
 * @param {{ts: string, nonce: number}|null} props.jumpToTs  Scroll/flash target
 */
const StreamChatReplay = ({
    messages,
    hasMore,
    isFetchingMore,
    onLoadMore,
    jumpToTs,
}) => {
    const virtuosoRef = useRef(null)
    // Remember which jump (by nonce) already scrolled, so growing `messages`
    // during load-more does not re-scroll and fight the user. A jump whose
    // target row is not loaded yet is left unhandled and retries as pages arrive.
    const handledNonceRef = useRef(null)

    const [
        flashId,
        setFlashId,
    ] = useState(null)

    useEffect(() => {
        const target = jumpToTs && (typeof jumpToTs === 'object' ? jumpToTs.ts : jumpToTs)
        const nonce = jumpToTs && typeof jumpToTs === 'object' ? jumpToTs.nonce : jumpToTs
        if (!target || handledNonceRef.current === nonce) {
            return undefined
        }
        const index = messages.findIndex(message => message.ts >= target)
        if (index < 0) {
            return undefined
        }
        handledNonceRef.current = nonce
        virtuosoRef.current?.scrollToIndex({
            index,
            align: 'start',
        })
        setFlashId(messages[index].id)
        const timer = setTimeout(() => setFlashId(null), 1600)
        return () => clearTimeout(timer)
    }, [
        jumpToTs,
        messages,
    ])

    const handleEndReached = useCallback(() => {
        if (hasMore && !isFetchingMore) {
            onLoadMore?.()
        }
    }, [
        hasMore,
        isFetchingMore,
        onLoadMore,
    ])

    const renderRow = useCallback((index, message) => {
        const badges = parseBadges(message.badges)
        return (
            <div
                className={`chat-line${message.id === flashId ? ' chat-line--flash' : ''}`}
                role="listitem">
                <span
                    className="chat-timestamp"
                    aria-hidden="true">
                    {clockFromTs(message.ts)}
                </span>
                {badges.length > 0 && (
                    <span
                        className="chat-badges"
                        aria-hidden="true">
                        {badges.map(badge => (badge.icon
                            ? (
                                <i
                                    key={badge.raw}
                                    className={`bi ${badge.icon} chat-badge ${badge.className}`}
                                    title={badge.raw}
                                />
                            )
                            : (
                                <span
                                    key={badge.raw}
                                    className={`chat-badge ${badge.className}`}
                                    title={badge.raw}
                                />
                            )))}
                    </span>
                )}
                <span
                    className="chat-nick"
                    style={{ color: nickColor(message.nick || '') }}>
                    {badges.length > 0 && (
                        <span className="visually-hidden">
                            {`${badges.map(badge => badge.label).join(', ')} `}
                        </span>
                    )}
                    {message.nick}
                </span>
                <span aria-hidden="true">: </span>
                <span className="chat-text">
                    {applyBetterTvEmotes(message.text)}
                </span>
            </div>
        )
    }, [
        flashId,
    ])

    const renderFooter = useCallback(() => (
        isFetchingMore
            ? (
                <div className="chat-replay-footer">
                    Loading more messages…
                </div>
            )
            : null
    ), [
        isFetchingMore,
    ])

    return (
        <div
            className="chat-panel"
            role="log"
            aria-live="polite"
            aria-label="Stream chat replay"
            tabIndex="0">
            <div
                className="chat-panel-head"
                aria-hidden="true">
                <i className="bi bi-chat-left-text"></i>
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
                <p className="text-muted small mb-0 px-3 py-3">
                    No messages match these filters.
                </p>
            )}
        </div>
    )
}

export default StreamChatReplay
