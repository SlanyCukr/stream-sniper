'use client'
import Select from 'react-select'
import { MOMENT_STATUS_TABS } from '@/lib/models/momentQueue'

const MomentFilters = ({
    statusKey,
    onStatusChange,
    creators,
    selectedCreator,
    onCreatorChange,
}) => (
    <div
        className="toolbar moment-toolbar"
        role="search"
        aria-label="Highlight queue filters">
        <div className="chatter-tabs" role="tablist" aria-label="Review status">
            {MOMENT_STATUS_TABS.map(tab => (
                <button
                    key={tab.key}
                    type="button"
                    role="tab"
                    id={`moment-tab-${tab.key}`}
                    aria-selected={statusKey === tab.key}
                    className={statusKey === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                    onClick={() => onStatusChange(tab.key)}>
                    {tab.label}
                </button>
            ))}
        </div>

        <div className="toolbar-field moment-creator-field">
            <label htmlFor="moment-creator-select" className="visually-hidden">
                Filter by creator
            </label>
            <Select
                classNamePrefix="rs"
                instanceId="moment-creator-select"
                inputId="moment-creator-select"
                options={creators}
                value={selectedCreator}
                onChange={onCreatorChange}
                placeholder="All creators..."
                isClearable
                aria-label="Filter by creator"
            />
        </div>
    </div>
)

export default MomentFilters
