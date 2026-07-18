'use client'

import Select from 'react-select'
import { SEARCH_DAY_WINDOWS } from '@/hooks/scene/searchUrlState'

interface CreatorOption {
  value: number
  label: string
}

interface SearchToolbarProps {
  input: string
  onInputChange: (value: string) => void
  creators: CreatorOption[]
  selectedCreator: CreatorOption | null
  onCreatorChange: (option: CreatorOption | null) => void
  days: number | null
  onDaysChange: (value: number | null) => void
}

const DAY_LABELS: Record<number, string> = {
  7: '7 days',
  30: '30 days',
  90: '90 days',
  365: '365 days',
}

const SearchToolbar = ({
  input, onInputChange, creators, selectedCreator, onCreatorChange, days, onDaysChange,
}: SearchToolbarProps) => (
  <div className="toolbar search-toolbar" role="search" aria-label="Chat search">
    <div className="toolbar-field search-query-field">
      <label htmlFor="scene-search-input" className="visually-hidden">Search chat messages</label>
      <input
        id="scene-search-input"
        type="search"
        className="form-control"
        placeholder="Search chat messages…"
        value={input}
        onChange={event => onInputChange(event.target.value)}
        maxLength={200}
        autoComplete="off"
      />
    </div>
    <div className="toolbar-field search-creator-field">
      <label htmlFor="scene-search-creator" className="visually-hidden">Filter by creator</label>
      <Select
        classNamePrefix="rs"
        instanceId="scene-search-creator"
        inputId="scene-search-creator"
        options={creators}
        value={selectedCreator}
        onChange={option => onCreatorChange((option as CreatorOption | null) ?? null)}
        placeholder="All creators…"
        isClearable
        aria-label="Filter by creator"
      />
    </div>
    <div className="toolbar-field search-days-field">
      <label htmlFor="scene-search-days" className="visually-hidden">Time window</label>
      <select
        id="scene-search-days"
        className="form-select"
        value={days ?? ''}
        onChange={event => onDaysChange(event.target.value ? Number(event.target.value) : null)}
      >
        <option value="">All time</option>
        {SEARCH_DAY_WINDOWS.map(window => (
          <option key={window} value={window}>{DAY_LABELS[window]}</option>
        ))}
      </select>
    </div>
  </div>
)

export default SearchToolbar
