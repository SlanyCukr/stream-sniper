'use client'
import Select from 'react-select'
import {
    Card,
} from 'react-bootstrap'
import LoadingSpinner from '../LoadingSpinner'
import ErrorAlert from '../ErrorAlert'

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
}) => (
    <Card>
        <Card.Body>
            <Card.Title
                as="h2"
                id="chat-search-heading">
                Searching for messages in this stream
            </Card.Title>
            <div
                role="search"
                aria-labelledby="chat-search-heading">
                <label
                    htmlFor="chatter-select"
                    className="visually-hidden">
                    Select a chatter to view their messages
                </label>
                <Select
                    inputId="chatter-select"
                    options={chattersInStream}
                    value={selectedChatterOption}
                    onChange={handleChatterSelection}
                    placeholder="Search for a chatter..."
                    isClearable
                    isSearchable
                    aria-describedby="chatter-select-help"
                />
                <div
                    id="chatter-select-help"
                    className="form-text">
                    Select a chatter to see their messages from this stream
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

export default ChatSearchCard
