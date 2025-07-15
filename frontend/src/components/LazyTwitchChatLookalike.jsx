import {
    lazy, Suspense,
} from 'react'
import PropTypes from 'prop-types'
import ChatLoadingFallback from './ChatLoadingFallback'

// Lazy load the TwitchChatLookalike component with emotes
const TwitchChatLookalike = lazy(() => import('./TwitchChatLookalike'))

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


LazyTwitchChatLookalike.propTypes = {
    nick: PropTypes.string.isRequired,
    messages: PropTypes.arrayOf(PropTypes.string).isRequired,
}

export default LazyTwitchChatLookalike

