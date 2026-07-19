import {
    nickColor, parseBadges, renderMessageWithBetterTtvEmotes,
} from '@/utils/chatRender'
import type { StreamMessage } from '@/hooks/stream/replay/useStreamMessagesQuery'

const clockFromTs = (timestamp: string | undefined): string => {
    if (!timestamp) return ''
    return (String(timestamp).split('T')[1] || '').slice(0, 8)
}

interface ChatReplayLineProps {
    message: StreamMessage
    isFlashing: boolean
}

const ChatReplayLine = ({
    message, isFlashing,
}: ChatReplayLineProps) => {
    const badges = parseBadges(message.badges)
    return (
        <div className={`chat-line${isFlashing ? ' chat-line--flash' : ''}`} role="listitem">
            <span className="chat-timestamp" aria-hidden="true">{clockFromTs(message.ts)}</span>
            {badges.length > 0 ? (
                <span className="chat-badges" aria-hidden="true">
                    {badges.map(badge => (badge.icon ? (
                        <i
                            key={badge.raw}
                            className={`bi ${badge.icon} chat-badge ${badge.className}`}
                            title={badge.raw}
                        />
                    ) : (
                        <span
                            key={badge.raw}
                            className={`chat-badge ${badge.className}`}
                            title={badge.raw}
                        />
                    )))}
                </span>
            ) : null}
            <span className="chat-nick" style={{ color: nickColor(message.nick || '') }}>
                {badges.length > 0 ? (
                    <span className="visually-hidden">
                        {`${badges.map(badge => badge.label).join(', ')} `}
                    </span>
                ) : null}
                {message.nick}
            </span>
            <span aria-hidden="true">: </span>
            <span className="chat-text">{renderMessageWithBetterTtvEmotes(message.text)}</span>
        </div>
    )
}

export default ChatReplayLine
