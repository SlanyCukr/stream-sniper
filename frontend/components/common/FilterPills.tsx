'use client'

/**
 * Pill-style toggle group for filters that reshape a single result set
 * (time windows, sort orders). Visually identical to TabList but announced
 * as toggle buttons (aria-pressed), NOT tabs: a tablist promises one
 * tabpanel per tab, and these controls have no such panels — they re-query
 * the same view. Use TabList only when each tab owns a real tabpanel.
 */

type FilterOption<K extends string | number> = { key: K, label: string }

type FilterPillsProps<K extends string | number> = {
  options: Array<FilterOption<K>>
  activeKey: K
  ariaLabel: string
  onChange: (key: K) => void
}

const FilterPills = <K extends string | number>({
  options, activeKey, ariaLabel, onChange,
}: FilterPillsProps<K>) => (
  <div className="chatter-tabs" role="group" aria-label={ariaLabel}>
    {options.map(option => (
      <button
        key={option.key}
        type="button"
        aria-pressed={activeKey === option.key}
        className={activeKey === option.key ? 'chatter-tab active' : 'chatter-tab'}
        onClick={() => onChange(option.key)}
      >
        {option.label}
      </button>
    ))}
  </div>
)

export default FilterPills
