'use client'
import { Form } from 'react-bootstrap'

const parseBooleanFilter = value => value === '' ? null : value === 'true'

const TrackedStreamerFilters = ({ filters, total, onChange }) => (
    <div className="toolbar">
        <span className="toolbar-label" aria-hidden="true">Filter</span>
        <div className="toolbar-field">
            <label htmlFor="tracking-status-filter" className="visually-hidden">
                Filter by status
            </label>
            <Form.Select
                id="tracking-status-filter"
                value={filters.isActive === null ? '' : String(filters.isActive)}
                onChange={event => onChange('isActive', parseBooleanFilter(event.target.value))}>
                <option value="">All statuses</option>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
            </Form.Select>
        </div>
        <div className="toolbar-field">
            <label htmlFor="tracking-processing-filter" className="visually-hidden">
                Filter by processing
            </label>
            <Form.Select
                id="tracking-processing-filter"
                value={filters.processingEnabled === null ? '' : String(filters.processingEnabled)}
                onChange={event => onChange('processingEnabled', parseBooleanFilter(event.target.value))}>
                <option value="">All processing</option>
                <option value="true">Processing enabled</option>
                <option value="false">Processing disabled</option>
            </Form.Select>
        </div>
        <span className="toolbar-readout">{total} tracked</span>
    </div>
)

export default TrackedStreamerFilters
