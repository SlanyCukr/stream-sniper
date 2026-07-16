'use client'
import {
    useCallback, useEffect, useMemo, useState,
} from 'react'
import Select from 'react-select'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'

const MAX_RENDERED_OPTIONS = 100

const StreamReplayFilters = ({
    chatterOptions,
    onChatterChange,
    onQueryChange,
    onSubOnlyChange,
}) => {
    const [selectedOption, setSelectedOption] = useState(null)
    const [optionInput, setOptionInput] = useState('')
    const [searchText, setSearchText] = useState('')
    const [subOnly, setSubOnly] = useState(false)
    const debouncedSearch = useDebouncedValue(searchText, 300)

    useEffect(() => {
        onQueryChange(debouncedSearch.trim() || undefined)
    }, [
        debouncedSearch,
        onQueryChange,
    ])

    const visibleOptions = useMemo(() => {
        const query = optionInput.trim().toLowerCase()
        const matches = query
            ? chatterOptions.filter(option => option.label?.toLowerCase().includes(query))
            : chatterOptions
        return matches.slice(0, MAX_RENDERED_OPTIONS)
    }, [
        chatterOptions,
        optionInput,
    ])

    const handleChatterSelect = useCallback(option => {
        setSelectedOption(option)
        onChatterChange(option?.value)
    }, [onChatterChange])

    const noOptionsMessage = useCallback(({ inputValue }) => (
        inputValue
            ? `No chatters matching "${inputValue}"`
            : 'No chatters recorded in this stream'
    ), [])

    return (
        <div className="replay-filters" role="search" aria-labelledby="chat-replay-heading">
            <div className="replay-filter">
                <label htmlFor="replay-chatter-select" className="visually-hidden">
                    Filter replay by chatter
                </label>
                <Select
                    classNamePrefix="rs"
                    instanceId="replay-chatter-select"
                    inputId="replay-chatter-select"
                    options={visibleOptions}
                    value={selectedOption}
                    onChange={handleChatterSelect}
                    onInputChange={value => {
                        setOptionInput(value)
                        return value
                    }}
                    filterOption={() => true}
                    noOptionsMessage={noOptionsMessage}
                    placeholder="All chatters..."
                    isClearable
                    isSearchable
                    aria-describedby="replay-chatter-help"
                />
                <div id="replay-chatter-help" className="form-text">
                    Type to search; the first {MAX_RENDERED_OPTIONS} matches are shown
                </div>
            </div>

            <div className="replay-filter">
                <label htmlFor="replay-text-search" className="visually-hidden">
                    Search message text
                </label>
                <input
                    id="replay-text-search"
                    type="search"
                    className="form-control"
                    value={searchText}
                    onChange={event => setSearchText(event.target.value)}
                    placeholder="Search message text..."
                    aria-describedby="replay-text-help"
                />
                <div id="replay-text-help" className="form-text">
                    Case-insensitive; matches anywhere in a message
                </div>
            </div>

            <div className="replay-filter replay-filter--toggle">
                <div className="form-check form-switch replay-sub-toggle">
                    <input
                        id="replay-sub-only"
                        type="checkbox"
                        role="switch"
                        className="form-check-input"
                        checked={subOnly}
                        onChange={event => {
                            setSubOnly(event.target.checked)
                            onSubOnlyChange(event.target.checked)
                        }}
                        aria-describedby="replay-sub-help"
                    />
                    <label htmlFor="replay-sub-only" className="form-check-label">
                        Subscribers only
                    </label>
                </div>
                <div id="replay-sub-help" className="form-text">
                    Show only messages from subscribers
                </div>
            </div>
        </div>
    )
}

export default StreamReplayFilters
