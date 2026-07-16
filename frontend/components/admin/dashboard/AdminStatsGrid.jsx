const STAT_TILES = [
    { key: 'totalUsers', label: 'Total users', featured: true },
    { key: 'activeUsers', label: 'Active users' },
    { key: 'adminUsers', label: 'Admin users' },
    { key: 'recentRegistrations', label: 'Recent registrations', hint: 'Last 24 hours' },
]

const AdminStatsGrid = ({ stats }) => (
    <div className="stat-grid mb-4">
        {STAT_TILES.map(tile => (
            <div className="stat-tile" key={tile.key}>
                <div className="stat-label">{tile.label}</div>
                <div className={tile.featured ? 'stat-value text-phosphor' : 'stat-value'}>
                    {stats[tile.key]}
                </div>
                {tile.hint ? <div className="stat-hint">{tile.hint}</div> : null}
            </div>
        ))}
    </div>
)

export default AdminStatsGrid
