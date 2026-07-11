'use client'
import React, {
    useCallback, useEffect, useState,
} from 'react'
import Select from 'react-select'
import { AVAILABLE_ORDERING } from '@/constants'

/**
 * Slim filter toolbar above the stream grid.
 * @param {Array} creators
 * @param {object} selectedCreator
 * @param {function} onCreatorChange
 * @param {object} selectedOrdering
 * @param {function} onOrderChange
 * @param {('asc'|'desc')} dir
 * @param {function} onDirToggle
 * @param {string} title
 * @param {function} onTitleChange
 * @param {string} dateFrom
 * @param {string} dateTo
 * @param {function} onDateFromChange
 * @param {function} onDateToChange
 * @param {boolean} dateRangeInvalid
 * @param {string} minMessages
 * @param {function} onMinMessagesCommit
 * @param {function} onReset
 * @param {boolean} showReset
 * @param {number} page
 * @param {number} pagesCount
 * @returns {JSX.Element}
 */
const FiltersCard = React.memo(({
    creators,
    selectedCreator,
    onCreatorChange,
    selectedOrdering,
    onOrderChange,
    dir,
    onDirToggle,
    title,
    onTitleChange,
    dateFrom,
    dateTo,
    onDateFromChange,
    onDateToChange,
    dateRangeInvalid,
    minMessages,
    onMinMessagesCommit,
    onReset,
    showReset,
    page,
    pagesCount,
}) => {
    // Min-messages commits on blur/Enter rather than on every keystroke, so it
    // needs its own uncommitted local echo of the field (synced back down when
    // the committed value changes elsewhere, e.g. Reset).
    const [
        localMinMessages,
        setLocalMinMessages,
    ] = useState(minMessages)

    useEffect(() => {
        setLocalMinMessages(minMessages)
    }, [
        minMessages,
    ])

    const commitMinMessages = useCallback(() => {
        if (localMinMessages !== minMessages) {
            onMinMessagesCommit(localMinMessages)
        }
    }, [
        localMinMessages,
        minMessages,
        onMinMessagesCommit,
    ])

    const handleMinMessagesKeyDown = useCallback(event => {
        if (event.key === 'Enter') {
            event.preventDefault()
            commitMinMessages()
            event.currentTarget.blur()
        }
    }, [
        commitMinMessages,
    ])

    return (
        <div
            className="toolbar"
            role="search"
            aria-label="Stream filters"
        >
            <span
                className="toolbar-label"
                aria-hidden="true">
                Filter
            </span>
            <div className="toolbar-field">
                <label
                    htmlFor="creator-select"
                    className="visually-hidden"
                >
                    Filter by creator
                </label>
                <Select
                    classNamePrefix="rs"
                    instanceId="creator-select"
                    inputId="creator-select"
                    options={creators}
                    value={selectedCreator}
                    onChange={onCreatorChange}
                    placeholder="All creators"
                    isClearable
                    aria-label="Filter streams by creator"
                    aria-describedby="creator-help"
                />
                <div
                    id="creator-help"
                    className="visually-hidden"
                >
                    Choose a specific creator to filter streams, or leave empty to show all streams
                </div>
            </div>
            <div className="toolbar-field toolbar-field--sort">
                <label
                    htmlFor="ordering-select"
                    className="visually-hidden"
                >
                    Sort streams by
                </label>
                <div className="toolbar-sort-group">
                    <Select
                        classNamePrefix="rs"
                        className="toolbar-sort-select"
                        instanceId="ordering-select"
                        inputId="ordering-select"
                        options={AVAILABLE_ORDERING}
                        value={selectedOrdering}
                        onChange={onOrderChange}
                        placeholder="Sort by..."
                        aria-label="Sort streams by different criteria"
                        aria-describedby="ordering-help"
                    />
                    <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm toolbar-dir-toggle"
                        onClick={onDirToggle}
                        aria-pressed={dir === 'asc'}
                        aria-label={dir === 'asc'
                            ? 'Sort direction ascending, activate to sort descending'
                            : 'Sort direction descending, activate to sort ascending'}
                        title={dir === 'asc' ? 'Ascending' : 'Descending'}
                    >
                        <i
                            className={`bi ${dir === 'asc' ? 'bi-sort-up' : 'bi-sort-down'}`}
                            aria-hidden="true"
                        />
                    </button>
                </div>
                <div
                    id="ordering-help"
                    className="visually-hidden"
                >
                    Choose how to sort the streams list, then toggle ascending or descending
                </div>
            </div>
            <div className="toolbar-field">
                <label
                    htmlFor="title-search"
                    className="visually-hidden"
                >
                    Search stream titles
                </label>
                <input
                    id="title-search"
                    type="search"
                    className="form-control"
                    placeholder="Search titles..."
                    value={title}
                    onChange={event => onTitleChange(event.target.value)}
                    aria-describedby="title-help"
                />
                <div
                    id="title-help"
                    className="visually-hidden"
                >
                    Filter streams by title text
                </div>
            </div>
            <div className="toolbar-field toolbar-field--dates">
                <div className="toolbar-date-group">
                    <div>
                        <label
                            htmlFor="date-from"
                            className="visually-hidden"
                        >
                            From date
                        </label>
                        <input
                            id="date-from"
                            type="date"
                            className="form-control"
                            value={dateFrom}
                            onChange={event => onDateFromChange(event.target.value)}
                            aria-describedby="date-range-help"
                            aria-invalid={dateRangeInvalid || undefined}
                        />
                    </div>
                    <span
                        className="toolbar-date-sep"
                        aria-hidden="true">
                        –
                    </span>
                    <div>
                        <label
                            htmlFor="date-to"
                            className="visually-hidden"
                        >
                            To date
                        </label>
                        <input
                            id="date-to"
                            type="date"
                            className="form-control"
                            value={dateTo}
                            onChange={event => onDateToChange(event.target.value)}
                            aria-describedby="date-range-help"
                            aria-invalid={dateRangeInvalid || undefined}
                        />
                    </div>
                </div>
                <div
                    id="date-range-help"
                    className={dateRangeInvalid ? 'toolbar-warning' : 'visually-hidden'}
                    role={dateRangeInvalid ? 'alert' : undefined}
                >
                    {dateRangeInvalid
                        ? '"From" date must be on or before "To" date — range ignored until fixed'
                        : 'Filter streams by start date range'
                    }
                </div>
            </div>
            <div className="toolbar-field toolbar-field--min-messages">
                <label
                    htmlFor="min-messages"
                    className="visually-hidden"
                >
                    Minimum messages
                </label>
                <input
                    id="min-messages"
                    type="number"
                    min="0"
                    className="form-control"
                    placeholder="Min messages"
                    value={localMinMessages}
                    onChange={event => setLocalMinMessages(event.target.value)}
                    onBlur={commitMinMessages}
                    onKeyDown={handleMinMessagesKeyDown}
                    aria-describedby="min-messages-help"
                />
                <div
                    id="min-messages-help"
                    className="visually-hidden"
                >
                    Only show streams with at least this many messages. Press Enter or leave the field to apply.
                </div>
            </div>
            {showReset && (
                <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm toolbar-reset"
                    onClick={onReset}
                >
                    Reset
                </button>
            )}
            {pagesCount > 0 && (
                <span className="toolbar-readout">
                    Page <strong>{page}</strong> / {pagesCount}
                </span>
            )}
        </div>
    )
})

FiltersCard.displayName = 'FiltersCard'

export default FiltersCard
