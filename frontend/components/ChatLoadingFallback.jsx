'use client'

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

export default ChatLoadingFallback
