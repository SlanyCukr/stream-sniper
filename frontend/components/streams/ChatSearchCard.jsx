'use client'
import {
    useState, useMemo, useCallback,
} from 'react'
import Select from 'react-select'
import {
    Card,
} from 'react-bootstrap'
import LoadingSpinner from '../LoadingSpinner'
import ErrorAlert from '../ErrorAlert'

/**
 * react-select renders every matching option into the DOM, which freezes the
 * UI when a stream has thousands of chatters. We pre-filter + cap the visible
 * options ourselves and disable react-select's own filtering.
 */
const MAX_RENDERED_OPTIONS = 100

/**
 * Chat Search Card Component
 */
const ChatSearchCard = ({
    chattersInStream,
    selectedChatterOption,
    handleChatterSelection,
    isMessagesLoading,
    messagesError,
    renderTwitchChat,
}) => {
    const [
        inputValue,
        setInputValue,
    ] = useState('')

    const handleInputChange = useCallback(value => {
        setInputValue(value)
        return value
    }, [
    ])

    const visibleOptions = useMemo(() => {
        const query = inputValue.trim().toLowerCase()
        const matches = query
            ? chattersInStream.filter(option => option.label?.toLowerCase().includes(query))
            : chattersInStream
        return matches.slice(0, MAX_RENDERED_OPTIONS)
    }, [
        chattersInStream,
        inputValue,
    ])

    const noOptionsMessage = useCallback(({ inputValue: query }) => (
        query
            ? `No chatters matching "${query}"`
            : 'No chatters recorded in this stream'
    ), [
    ])

    return (
        <Card>
            <Card.Body>
                <h2
                    className="section-label mb-1"
                    id="chat-search-heading">
                    Chat replay
                </h2>
                <p className="text-muted small mb-3">
                    {chattersInStream.length.toLocaleString()} chatters recorded — pick one to replay their messages.
                </p>
                <div
                    role="search"
                    aria-labelledby="chat-search-heading">
                    <label
                        htmlFor="chatter-select"
                        className="visually-hidden">
                        Select a chatter to view their messages
                    </label>
                    <Select
                        instanceId="chatter-select"
                        inputId="chatter-select"
                        options={visibleOptions}
                        value={selectedChatterOption}
                        onChange={handleChatterSelection}
                        onInputChange={handleInputChange}
                        filterOption={() => true}
                        noOptionsMessage={noOptionsMessage}
                        placeholder="Search for a chatter..."
                        isClearable
                        isSearchable
                        aria-describedby="chatter-select-help"
                    />
                    <div
                        id="chatter-select-help"
                        className="form-text">
                        Type to search; the first {MAX_RENDERED_OPTIONS} matches are shown
                    </div>
                </div>

                {isMessagesLoading && (
                    <LoadingSpinner
                        text="Loading messages..."
                        className="mt-3" />
                )}

                {messagesError && (
                    <ErrorAlert
                        error={messagesError}
                        title="Failed to load messages"
                        className="mt-3"
                    />
                )}

                {renderTwitchChat}
            </Card.Body>
        </Card>
    )
}

export default ChatSearchCard
