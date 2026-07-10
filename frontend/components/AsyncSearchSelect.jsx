'use client'
import { useCallback, useRef } from 'react'
import AsyncSelect from 'react-select/async'
import AsyncCreatableSelect from 'react-select/async-creatable'

/**
 * Debounced async react-select wrapper for server-backed autocomplete.
 *
 * react-select's AsyncSelect calls loadOptions on every keystroke; we wrap it in
 * a small setTimeout debounce so a suggestion request only fires once the user
 * pauses typing. Set `creatable` to allow selecting a value the search didn't
 * surface (used by the add-streamer field, since Twitch search only returns
 * channels active in the last 6 months).
 *
 * @param {object} props
 * @param {(query: string) => Promise<Array>} props.loadOptions - returns option objects
 * @param {number} [props.debounceMs=300] - debounce window in milliseconds
 * @param {boolean} [props.creatable=false] - allow free-text created options
 */
const DEFAULT_DEBOUNCE_MS = 300

const AsyncSearchSelect = ({
    loadOptions,
    debounceMs = DEFAULT_DEBOUNCE_MS,
    creatable = false,
    ...selectProps
}) => {
    const timerRef = useRef(null)

    const debouncedLoadOptions = useCallback(inputValue => new Promise((resolve, reject) => {
        if (timerRef.current) {
            clearTimeout(timerRef.current)
        }
        timerRef.current = setTimeout(() => {
            Promise.resolve(loadOptions(inputValue)).then(resolve, reject)
        }, debounceMs)
    }), [
        loadOptions,
        debounceMs,
    ])

    const SelectComponent = creatable ? AsyncCreatableSelect : AsyncSelect

    return (
        <SelectComponent
            classNamePrefix="rs"
            loadOptions={debouncedLoadOptions}
            {...selectProps}
        />
    )
}

export default AsyncSearchSelect
