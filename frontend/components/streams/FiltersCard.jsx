'use client'
import React from 'react'
import Select from 'react-select'
import { AVAILABLE_ORDERING } from '@/constants'

/**
 * Slim filter toolbar above the stream grid.
 * @param {Array} creators
 * @param {object} selectedCreator
 * @param {function} onCreatorChange
 * @param {object} selectedOrdering
 * @param {function} onOrderingChange
 * @param {number} page
 * @param {number} pagesCount
 * @returns {JSX.Element}
 */
const FiltersCard = React.memo(({
    creators,
    selectedCreator,
    onCreatorChange,
    selectedOrdering,
    onOrderingChange,
    page,
    pagesCount,
}) => (
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
        <div className="toolbar-field">
            <label
                htmlFor="ordering-select"
                className="visually-hidden"
            >
                Sort streams by
            </label>
            <Select
                instanceId="ordering-select"
                inputId="ordering-select"
                options={AVAILABLE_ORDERING}
                value={selectedOrdering}
                onChange={onOrderingChange}
                placeholder="Sort by..."
                aria-label="Sort streams by different criteria"
                aria-describedby="ordering-help"
            />
            <div
                id="ordering-help"
                className="visually-hidden"
            >
                Choose how to sort the streams list
            </div>
        </div>
        {pagesCount > 0 && (
            <span className="toolbar-readout">
                Page <strong>{page}</strong> / {pagesCount}
            </span>
        )}
    </div>
))

FiltersCard.displayName = 'FiltersCard'

export default FiltersCard
