import type { ReactNode } from 'react'

interface StreamMetricTileProps {
    label: string
    value: ReactNode
    phosphor?: boolean
    hint?: ReactNode
    children?: ReactNode
}

const StreamMetricTile = ({
    label, value, phosphor = false, hint = null, children = null,
}: StreamMetricTileProps) => (
    <div className="stat-tile" role="listitem">
        <div className="stat-label">{label}</div>
        <div className={`stat-value${phosphor ? ' text-phosphor' : ''}`}>
            {value}
            {children}
        </div>
        {hint ? <div className="stat-hint">{hint}</div> : null}
    </div>
)

export default StreamMetricTile
