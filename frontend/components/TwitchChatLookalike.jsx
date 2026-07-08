'use client'
import React, {
    useMemo,
    useCallback,
} from 'react'
import { Virtuoso } from 'react-virtuoso'
import { EMOTES } from '@/lib/bettertv_emotes'

/* Twitch-style username palette (dark-theme readable). */
const NICK_COLORS = [
    '#ff7a7a',
    '#f5b759',
    '#9fef00',
    '#2dd4a7',
    '#58a6ff',
    '#c58fff',
    '#ff8fd0',
    '#5edfff',
    '#ffb86b',
    '#a3e635',
]

/** Deterministic color per nick so it stays stable across renders. */
const nickColor = nick => {
    let hash = 0
    for (let i = 0; i < nick.length; i++) {
        hash = (hash * 31 + nick.charCodeAt(i)) | 0
    }
    return NICK_COLORS[Math.abs(hash) % NICK_COLORS.length]
}

const TwitchChatLookalike = ({
    nick,
    messages,
}) => {
    /**
     * Applies BetterTV emotes to the message with memoization.
     * @param {string} message
     * @returns {JSX.Element}
     */
    const applyBetterTvEmotes = useCallback(message => {
        if (!message) {
            return null
        }

        return message
            .split(' ')
            .map((word, index) => {
                if (word in EMOTES) {
                    return (
                        <img
                            key={index}
                            src={`https://cdn.betterttv.net/emote/${EMOTES[word]}/1x`}
                            alt={word}
                            role="img"
                            aria-label={`${word} emote`}
                        />
                    )
                }

                return <span key={index}>{word + ' '}</span>
            })
    }, [
    ])

    const color = useMemo(() => nickColor(nick || ''), [
        nick,
    ])

    // Virtualized row renderer — only visible messages hit the DOM
    const renderLine = useCallback((index, message) => (
        <p
            className="chat-line"
            role="listitem"
        >
            <span
                className="chat-nick"
                style={{ color }}
            >
                {nick}
            </span>
            <span aria-hidden="true">: </span>
            <span>
                {applyBetterTvEmotes(message)}
            </span>
        </p>
    ), [
        color,
        nick,
        applyBetterTvEmotes,
    ])

    const hasMessages = messages && messages.length > 0
    // Keep short replays compact instead of forcing a tall empty panel
    const panelHeight = useMemo(() => Math.min(480, Math.max(120, (messages?.length || 0) * 32)), [
        messages?.length,
    ])

    return (
        <div
            className="chat-panel"
            role="log"
            aria-live="polite"
            aria-label={`Chat messages from ${nick}`}
            tabIndex="0"
        >
            <div
                className="chat-panel-head"
                aria-hidden="true">
                <i className="bi bi-chat-left-text"></i>
                <span>Chat replay // {nick}</span>
                <span className="chat-count">{(messages?.length || 0).toLocaleString()} msgs</span>
            </div>
            <div
                className="chat-panel-body"
                role="list"
                aria-label={`${messages?.length || 0} messages from ${nick}`}>
                {hasMessages ? (
                    <Virtuoso
                        data={messages}
                        itemContent={renderLine}
                        style={{ height: `${panelHeight}px` }}
                    />
                ) : (
                    <p className="text-muted small mb-0 py-2">No messages recorded for this chatter.</p>
                )}
            </div>
        </div>
    )
}

// Custom comparison function for React.memo
const areEqual = (prevProps, nextProps) => {
    // Compare nick
    if (prevProps.nick !== nextProps.nick) {
        return false
    }

    // Compare messages array length first (fast check)
    if (prevProps.messages.length !== nextProps.messages.length) {
        return false
    }

    // Compare each message in the array
    for (let i = 0; i < prevProps.messages.length; i++) {
        if (prevProps.messages[i] !== nextProps.messages[i]) {
            return false
        }
    }

    return true
}

export default React.memo(TwitchChatLookalike, areEqual)
