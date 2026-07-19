import { useRef, useState } from 'react'
import type { ChangeEvent, KeyboardEvent } from 'react'

interface MinimumMessagesFilterProps {
    value: string
    onCommit: (value: string) => void
}

const MinimumMessagesFilter = ({
    value,
    onCommit,
}: MinimumMessagesFilterProps) => {
    const skipNextBlurRef = useRef(false)
    const [draft, setDraft] = useState({
        base: value,
        value,
    })
    const localValue = draft.base === value ? draft.value : value

    const commit = () => {
        if (localValue !== value) onCommit(localValue)
    }

    const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
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
                onChange={(event: ChangeEvent<HTMLInputElement>) => setDraft({
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
