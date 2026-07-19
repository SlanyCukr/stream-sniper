import Select from 'react-select'

interface OrderingOption {
    label: string
    value: string
}

interface StreamSortControlsProps {
    ordering: OrderingOption[]
    order: OrderingOption | null
    direction: 'asc' | 'desc'
    onOrderChange: (value: OrderingOption | null) => void
    onDirectionChange: () => void
}

const StreamSortControls = ({
    ordering,
    order,
    direction,
    onOrderChange,
    onDirectionChange,
}: StreamSortControlsProps) => (
    <div className="toolbar-field toolbar-field--sort">
        <label
            htmlFor="ordering-select"
            className="visually-hidden">
            Sort streams by
        </label>
        <div className="toolbar-sort-group">
            <Select
                classNamePrefix="rs"
                className="toolbar-sort-select"
                instanceId="ordering-select"
                inputId="ordering-select"
                options={ordering}
                value={order}
                onChange={onOrderChange}
                placeholder="Sort by..."
                aria-label="Sort streams by different criteria"
                aria-describedby="ordering-help"
            />
            <button
                type="button"
                className="btn btn-outline-secondary btn-sm toolbar-dir-toggle"
                onClick={onDirectionChange}
                aria-pressed={direction === 'asc'}
                aria-label={direction === 'asc'
                    ? 'Sort direction ascending, activate to sort descending'
                    : 'Sort direction descending, activate to sort ascending'}
                title={direction === 'asc' ? 'Ascending' : 'Descending'}>
                <i
                    className={`bi ${direction === 'asc' ? 'bi-sort-up' : 'bi-sort-down'}`}
                    aria-hidden="true" />
            </button>
        </div>
        <div
            id="ordering-help"
            className="visually-hidden">
            Choose how to sort the streams list, then toggle ascending or descending
        </div>
    </div>
)

export default StreamSortControls
