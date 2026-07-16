const TabList = ({
    tabs, activeKey, idPrefix, ariaLabel, onChange,
}) => (
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
