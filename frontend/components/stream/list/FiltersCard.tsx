'use client'
import type { ChangeEvent } from 'react'
import type { CreatorOption } from '@/hooks/creator/useCreatorsQuery'
import CreatorFilter from './CreatorFilter'
import DateRangeFilter from './DateRangeFilter'
import MinimumMessagesFilter from './MinimumMessagesFilter'
import StreamSortControls from './StreamSortControls'

interface OrderingOption {
    label: string
    value: string
}

interface StreamFilters {
    creator: CreatorOption | null
    order: OrderingOption | null
    dir: 'asc' | 'desc'
    title: string
    dateFrom: string
    dateTo: string
    minMessages: string
}

type StreamFilterKey = keyof StreamFilters

interface FilterOptions {
    creators: CreatorOption[]
    ordering: OrderingOption[]
}

interface FilterValidation {
    dateRangeInvalid: boolean
    showReset: boolean
}

interface FilterPagination {
    pageIndex: number
    pageCount: number
}

interface FiltersCardProps {
    filters: StreamFilters
    options: FilterOptions
    validation: FilterValidation
    pagination: FilterPagination
    onFilterChange: (key: StreamFilterKey, value: StreamFilters[StreamFilterKey]) => void
    onReset: () => void
}

function FiltersCard({
    filters,
    options,
    validation,
    pagination,
    onFilterChange,
    onReset,
}: FiltersCardProps) {
    const {
        creator, order, dir, title, dateFrom, dateTo, minMessages,
    } = filters
    const { creators, ordering } = options
    const { dateRangeInvalid, showReset } = validation
    const { pageIndex, pageCount } = pagination

    const handleCreatorChange = (value: CreatorOption | null) => onFilterChange('creator', value)
    const handleOrderChange = (value: OrderingOption | null) => onFilterChange('order', value)
    const handleDateFromChange = (event: ChangeEvent<HTMLInputElement>) => onFilterChange('dateFrom', event.target.value)
    const handleDateToChange = (event: ChangeEvent<HTMLInputElement>) => onFilterChange('dateTo', event.target.value)
    const handleMinimumMessagesCommit = (value: string) => onFilterChange('minMessages', value)

    return (
        <div
            className="toolbar"
            role="search"
            aria-label="Stream filters">
            <span
                className="toolbar-label"
                aria-hidden="true">
                Filter
            </span>
            <CreatorFilter
                creators={creators}
                value={creator}
                onChange={handleCreatorChange} />
            <StreamSortControls
                ordering={ordering}
                order={order}
                direction={dir}
                onOrderChange={handleOrderChange}
                onDirectionChange={() => onFilterChange('dir', dir === 'asc' ? 'desc' : 'asc')} />
            <div className="toolbar-field">
                <label
                    htmlFor="title-search"
                    className="visually-hidden">
                    Search stream titles
                </label>
                <input
                    id="title-search"
                    type="search"
                    className="form-control"
                    placeholder="Search titles..."
                    value={title}
                    onChange={event => onFilterChange('title', event.target.value)}
                    aria-describedby="title-help" />
                <div
                    id="title-help"
                    className="visually-hidden">
                    Filter streams by title text
                </div>
            </div>
            <DateRangeFilter
                dateFrom={dateFrom}
                dateTo={dateTo}
                invalid={dateRangeInvalid}
                onFromChange={handleDateFromChange}
                onToChange={handleDateToChange} />
            <MinimumMessagesFilter
                value={minMessages}
                onCommit={handleMinimumMessagesCommit} />
            {showReset && (
                <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm toolbar-reset"
                    onClick={onReset}>
                    Reset
                </button>
            )}
            {pageCount > 0 && (
                <span className="toolbar-readout">
                    Page <strong>{pageIndex + 1}</strong> / {pageCount}
                </span>
            )}
        </div>
    )
}

export default FiltersCard
