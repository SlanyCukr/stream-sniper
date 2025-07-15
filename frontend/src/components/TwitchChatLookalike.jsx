import React, {
    useMemo,
    useCallback,
} from 'react'
import { EMOTES } from '../bettertv_emotes'
import PropTypes from 'prop-types'

const TwitchChatLookalike = ({
    nick,
    messages,
}) => {
    const generateRandomColor = () => {

        while(true){
            let randomHue = Math.random() * 360
            if ((randomHue >= 45 && randomHue <= 90) || (randomHue >= 140 && randomHue <= 195)){
                continue
            }

            const randomColor = `hsla(${randomHue}, 100%, 50%, 1)`
            return randomColor
        }
    }

    /**
     * Applies BetterTV emotes to the message with memoization.
     * @param {string} message
     * @returns {JSX.Element}
     * @example
     * // returns <img src="https://cdn.betterttv.net/emote/5e1a9a9f6b77c70ebf4b3b7f/1x" alt="LUL" />
     * applyBetterTvEmotes('LUL')
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

    // Memoize the random color to prevent regeneration on every render
    const randomColor = useMemo(() => generateRandomColor(), [
    ])

    // Memoize the processed messages to avoid re-processing on every render
    const processedMessages = useMemo(() => {
        if (!messages || messages.length === 0) {
            return null
        }

        return messages.map((message, index) => (
            <div
                key={index}
                className='my-2'
                role="listitem"
                aria-label={`Message ${index + 1} from ${nick}: ${message}`}
            >
                <span
                    style={{ color: randomColor }}
                    aria-label={`Message from ${nick}`}
                >
                    {nick}
                </span>
                <span aria-hidden="true">: </span>
                <span role="text">
                    {applyBetterTvEmotes(message)}
                </span>
            </div>
        ))
    }, [
        messages,
        randomColor,
        nick,
        applyBetterTvEmotes,
    ])

    return (
        <div
            className="my-3"
            role="log"
            aria-live="polite"
            aria-label={`Chat messages from ${nick}`}
            tabIndex="0"
        >
            <div
                role="list"
                aria-label={`${messages?.length || 0} messages from ${nick}`}>
                {processedMessages}
            </div>
        </div>
    )
}
TwitchChatLookalike.propTypes = {
    nick: PropTypes.string.isRequired,
    messages: PropTypes.arrayOf(PropTypes.string).isRequired,
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
