'use client'

/**
 * System Health Overview Stat Tiles
 */
const SystemHealthOverview = ({
    healthData, formatUptime, getStatusBadge,
}) => (
    <div className="stat-grid mb-4">
        <div className="stat-tile">
            <div className="stat-label">System status</div>
            <div className="stat-value">
                {getStatusBadge(healthData.status)}
            </div>
            <div className="stat-hint mono">
                Updated {new Date(healthData.timestamp).toLocaleString()}
            </div>
        </div>
        <div className="stat-tile">
            <div className="stat-label">Uptime</div>
            <div className="stat-value text-phosphor mono">
                {formatUptime(healthData.uptime_seconds)}
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
                {healthData.system?.memory_usage_percent?.toFixed(1)}%
            </div>
            <div className="stat-hint">of system memory</div>
        </div>
    </div>
)

export default SystemHealthOverview
