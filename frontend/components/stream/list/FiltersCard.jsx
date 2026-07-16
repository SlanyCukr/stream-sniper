// @ts-check
'use client'
import CreatorFilter from './CreatorFilter'
import DateRangeFilter from './DateRangeFilter'
import MinimumMessagesFilter from './MinimumMessagesFilter'
import StreamSortControls from './StreamSortControls'

/** @typedef {{label:string, value:number}} CreatorOption */
/** @typedef {{label:string, value:string}} OrderingOption */
/** @typedef {{
 * creator: CreatorOption|null,
 * order: OrderingOption|null,
 * dir: 'asc'|'desc',
 * title: string,
 * dateFrom: string,
 * dateTo: string,
 * minMessages: string,
 * }} StreamFilters */
/** @typedef {'creator'|'order'|'dir'|'title'|'dateFrom'|'dateTo'|'minMessages'} StreamFilterKey */
/** @typedef {{creators: CreatorOption[], ordering: OrderingOption[]}} FilterOptions */
/** @typedef {{dateRangeInvalid: boolean, showReset: boolean}} FilterValidation */
/** @typedef {{pageIndex: number, pageCount: number}} FilterPagination */
/** @typedef {{
 * filters: StreamFilters,
 * options: FilterOptions,
 * validation: FilterValidation,
 * pagination: FilterPagination,
 * onFilterChange: (key: StreamFilterKey, value: any) => void,
 * onReset: () => void,
 * }} FiltersCardProps */

/** @param {FiltersCardProps} props */
function FiltersCard({
    filters,
    options,
    validation,
    pagination,
    onFilterChange,
    onReset,
}) {
    const {
        creator, order, dir, title, dateFrom, dateTo, minMessages,
    } = filters
    const { creators, ordering } = options
    const { dateRangeInvalid, showReset } = validation
    const { pageIndex, pageCount } = pagination

    /** @param {CreatorOption|null} value */
    const handleCreatorChange = value => onFilterChange('creator', value)
    /** @param {OrderingOption|null} value */
    const handleOrderChange = value => onFilterChange('order', value)
    /** @param {React.ChangeEvent<HTMLInputElement>} event */
    const handleDateFromChange = event => onFilterChange('dateFrom', event.target.value)
    /** @param {React.ChangeEvent<HTMLInputElement>} event */
    const handleDateToChange = event => onFilterChange('dateTo', event.target.value)
    /** @param {string} value */
    const handleMinimumMessagesCommit = value => onFilterChange('minMessages', value)

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
