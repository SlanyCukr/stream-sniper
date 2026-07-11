'use client'
import {
    useState,
    useMemo,
    useEffect,
    useCallback,
} from 'react'
import Select from 'react-select'
import {
    Card,
} from 'react-bootstrap'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import LoadingSpinner from '../LoadingSpinner'
import ErrorAlert from '../ErrorAlert'
import StreamChatReplay from './StreamChatReplay'

/**
 * react-select renders every matching option into the DOM, which freezes the
 * UI when a stream has thousands of chatters. We pre-filter + cap the visible
 * options ourselves and disable react-select's own filtering.
 */
const MAX_RENDERED_OPTIONS = 100

/**
 * Stream chat-replay card: a chatter picker + a message text search, both
 * applied server-side. The parent owns the `useStreamMessages` infinite query
 * (so the timeline jump handler can drive `fetchNextPage`); this card reports
 * filter changes up via `onChatterChange` / `onQueryChange` and renders the
 * virtualized replay.
 * @param {object} props
 * @param {Array} props.chatterOptions        [{label, value}] from streamInfo.cis
 * @param {Function} props.onChatterChange     Receives the selected chatter id | undefined
 * @param {Function} props.onQueryChange       Receives the debounced text query
 * @param {Array} props.messages               Flattened replay rows
 * @param {boolean} props.hasMore              Another page can be fetched
 * @param {boolean} props.isFetchingMore       A page fetch is in flight
 * @param {Function} props.onLoadMore          Requests the next page
 * @param {boolean} props.isLoading            Initial page is loading
 * @param {*} props.error                      Query error, if any
 * @param {{ts: string, nonce: number}|null} props.jumpToTs  Scroll/flash target
 */
const StreamReplayCard = ({
    chatterOptions,
    onChatterChange,
    onQueryChange,
    messages,
    hasMore,
    isFetchingMore,
    onLoadMore,
    isLoading,
    error,
    jumpToTs,
}) => {
    const [
        selectedOption,
        setSelectedOption,
    ] = useState(null)
    const [
        optionInput,
        setOptionInput,
    ] = useState('')
    const [
        searchText,
        setSearchText,
    ] = useState('')

    const debouncedSearch = useDebouncedValue(searchText, 300)

    useEffect(() => {
        onQueryChange(debouncedSearch.trim() || undefined)
    }, [
        debouncedSearch,
        onQueryChange,
    ])

    const handleChatterSelect = useCallback(option => {
        setSelectedOption(option)
        onChatterChange(option?.value)
    }, [
        onChatterChange,
    ])

    const handleOptionInput = useCallback(value => {
        setOptionInput(value)
        return value
    }, [
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
                    id="chat-replay-heading">
                    Chat replay
                </h2>
                <p className="text-muted small mb-3">
                    {chatterOptions.length.toLocaleString()} chatters recorded — filter by chatter or search the text.
                </p>

                <div
                    className="replay-filters"
                    role="search"
                    aria-labelledby="chat-replay-heading">
                    <div className="replay-filter">
                        <label
                            htmlFor="replay-chatter-select"
                            className="visually-hidden">
                            Filter replay by chatter
                        </label>
                        <Select
                            classNamePrefix="rs"
                            instanceId="replay-chatter-select"
                            inputId="replay-chatter-select"
                            options={visibleOptions}
                            value={selectedOption}
                            onChange={handleChatterSelect}
                            onInputChange={handleOptionInput}
                            filterOption={() => true}
                            noOptionsMessage={noOptionsMessage}
                            placeholder="All chatters..."
                            isClearable
                            isSearchable
                            aria-describedby="replay-chatter-help"
                        />
                        <div
                            id="replay-chatter-help"
                            className="form-text">
                            Type to search; the first {MAX_RENDERED_OPTIONS} matches are shown
                        </div>
                    </div>

                    <div className="replay-filter">
                        <label
                            htmlFor="replay-text-search"
                            className="visually-hidden">
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
                        <div
                            id="replay-text-help"
                            className="form-text">
                            Case-insensitive; matches anywhere in a message
                        </div>
                    </div>
                </div>

                {error && (
                    <ErrorAlert
                        error={error}
                        title="Failed to load messages"
                        className="mt-3"
                    />
                )}

                {isLoading && !error ? (
                    <LoadingSpinner
                        text="Loading messages..."
                        className="mt-3" />
                ) : (
                    !error && (
                        <StreamChatReplay
                            messages={messages}
                            hasMore={hasMore}
                            isFetchingMore={isFetchingMore}
                            onLoadMore={onLoadMore}
                            jumpToTs={jumpToTs}
                        />
                    )
                )}
            </Card.Body>
        </Card>
    )
}

export default StreamReplayCard
