'use client'
import type { ReactNode } from 'react'
import type { DetailedHealth } from '@/hooks/admin/system/useSystemQueries'

interface SystemHealthOverviewProps {
    healthData: DetailedHealth
    formatUptime: (seconds: number) => string
    renderStatusBadge: (status: string) => ReactNode
}

const SystemHealthOverview = ({
    healthData, formatUptime, renderStatusBadge,
}: SystemHealthOverviewProps) => (
    <div className="stat-grid mb-4">
        <div className="stat-tile">
            <div className="stat-label">System status</div>
            <div className="stat-value">
                {renderStatusBadge(healthData.status)}
            </div>
            <div className="stat-hint mono">
                Updated {new Date(healthData.timestamp).toLocaleString()}
            </div>
        </div>
        <div className="stat-tile">
            <div className="stat-label">Uptime</div>
            <div className="stat-value text-phosphor mono">
                {formatUptime(healthData.uptimeSeconds)}
            </div>
            <div className="stat-hint">since last restart</div>
        </div>
        <div className="stat-tile">
            <div className="stat-label">Version</div>
            <div className="stat-value mono">{healthData.version}</div>
            <div className="stat-hint">API build</div>
        </div>
        <div className="stat-tile">
            <div className="stat-label">Memory usage</div>
            <div className="stat-value mono">
                {healthData.memoryUsagePercent?.toFixed(1)}%
            </div>
            <div className="stat-hint">of system memory</div>
        </div>
    </div>
)

export default SystemHealthOverview
