import { useRef, useState } from 'react'

const MinimumMessagesFilter = ({
    value,
    onCommit,
}) => {
    const skipNextBlurRef = useRef(false)
    const [draft, setDraft] = useState({
        base: value,
        value,
    })
    const localValue = draft.base === value ? draft.value : value

    const commit = () => {
        if (localValue !== value) onCommit(localValue)
    }

    const handleKeyDown = event => {
        if (event.key !== 'Enter') return
        event.preventDefault()
        commit()
        skipNextBlurRef.current = true
        event.currentTarget.blur()
    }

    const handleBlur = () => {
        if (skipNextBlurRef.current) {
            skipNextBlurRef.current = false
            return
        }
        commit()
    }

    return (
        <div className="toolbar-field toolbar-field--min-messages">
            <label
                htmlFor="min-messages"
                className="visually-hidden">
                Minimum messages
            </label>
            <input
                id="min-messages"
                type="number"
                min="0"
                className="form-control"
                placeholder="Min messages"
                value={localValue}
                onChange={event => setDraft({
                    base: value,
                    value: event.target.value,
                })}
                onBlur={handleBlur}
                onKeyDown={handleKeyDown}
                aria-describedby="min-messages-help" />
            <div
                id="min-messages-help"
                className="visually-hidden">
                Only show streams with at least this many messages. Press Enter or leave the field to apply.
            </div>
        </div>
    )
}

export default MinimumMessagesFilter
