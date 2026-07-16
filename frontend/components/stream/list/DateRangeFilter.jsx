const DateRangeFilter = ({
    dateFrom,
    dateTo,
    invalid,
    onFromChange,
    onToChange,
}) => (
    <div className="toolbar-field toolbar-field--dates">
        <div className="toolbar-date-group">
            <div>
                <label
                    htmlFor="date-from"
                    className="visually-hidden">
                    From date
                </label>
                <input
                    id="date-from"
                    type="date"
                    className="form-control"
                    value={dateFrom}
                    onChange={onFromChange}
                    aria-describedby="date-range-help"
                    aria-invalid={invalid || undefined} />
            </div>
            <span
                className="toolbar-date-sep"
                aria-hidden="true">
                –
            </span>
            <div>
                <label
                    htmlFor="date-to"
                    className="visually-hidden">
                    To date
                </label>
                <input
                    id="date-to"
                    type="date"
                    className="form-control"
                    value={dateTo}
                    onChange={onToChange}
                    aria-describedby="date-range-help"
                    aria-invalid={invalid || undefined} />
            </div>
        </div>
        <div
            id="date-range-help"
            className={invalid ? 'toolbar-warning' : 'visually-hidden'}
            role={invalid ? 'alert' : undefined}>
            {invalid
                ? '"From" date must be on or before "To" date — range ignored until fixed'
                : 'Filter streams by start date range'}
        </div>
    </div>
)

export default DateRangeFilter
