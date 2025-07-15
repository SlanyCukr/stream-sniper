import PropTypes from 'prop-types'

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

ChatLoadingFallback.propTypes = {
    nick: PropTypes.string.isRequired,
    messages: PropTypes.arrayOf(PropTypes.string).isRequired,
}

export default ChatLoadingFallback
