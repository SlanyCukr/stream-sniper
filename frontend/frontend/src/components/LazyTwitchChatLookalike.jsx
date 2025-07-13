import React, {
    lazy, Suspense,
} from 'react'
import PropTypes from 'prop-types'

// Lazy load the TwitchChatLookalike component with emotes
const TwitchChatLookalike = lazy(() => import('./TwitchChatLookalike'))

/**
 * Loading fallback component for chat messages
 */
const ChatLoadingFallback = ({
    nick, messages,
}) => (
    <div className="my-3">
        {messages.map((message, index) => (
            <div
                key={index}
                className='my-2'>
                <span style={{
                    color: '#9146ff',
                }}>{nick}</span>: {message}
            </div>
        ))}
    </div>
)

/**
 * Lazy-loaded wrapper for TwitchChatLookalike component
 * This ensures the heavy BetterTV emotes data is only loaded when needed
 */
const LazyTwitchChatLookalike = ({
    nick, messages,
}) => (
    <Suspense fallback={<ChatLoadingFallback
        nick={nick}
        messages={messages} />}>
        <TwitchChatLookalike
            nick={nick}
            messages={messages} />
    </Suspense>
)

ChatLoadingFallback.propTypes = {
    nick: PropTypes.string.isRequired,
    messages: PropTypes.arrayOf(PropTypes.string).isRequired,
}

LazyTwitchChatLookalike.propTypes = {
    nick: PropTypes.string.isRequired,
    messages: PropTypes.arrayOf(PropTypes.string).isRequired,
}

export default LazyTwitchChatLookalike

