import type { ReactNode } from 'react'

interface Tab<K extends string> {
    key: K
    label: ReactNode
}

interface TabListProps<K extends string> {
    tabs: Array<Tab<K>>
    activeKey: K
    idPrefix: string
    ariaLabel: string
    onChange: (key: K) => void
}

const TabList = <K extends string>({
    tabs, activeKey, idPrefix, ariaLabel, onChange,
}: TabListProps<K>) => (
    <div className="chatter-tabs" role="tablist" aria-label={ariaLabel}>
        {tabs.map(tab => (
            <button
                key={tab.key}
                type="button"
                role="tab"
                id={`${idPrefix}-tab-${tab.key}`}
                aria-selected={activeKey === tab.key}
                aria-controls={`${idPrefix}-panel-${tab.key}`}
                className={activeKey === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                onClick={() => onChange(tab.key)}
            >
                {tab.label}
            </button>
        ))}
    </div>
)

export default TabList
