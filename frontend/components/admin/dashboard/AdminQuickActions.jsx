import Link from 'next/link'
import { Card } from 'react-bootstrap'

const ACTIONS = [
    { href: '/admin/users', icon: 'bi-people', label: 'Manage Users', primary: true },
    { href: '/admin/users/create', icon: 'bi-person-plus', label: 'Create New User' },
    { href: '/admin/tracking', icon: 'bi-broadcast', label: 'Stream Tracking' },
    { href: '/admin/system', icon: 'bi-gear', label: 'System Information' },
]

const AdminQuickActions = () => (
    <Card className="mb-4">
        <Card.Body>
            <h3 className="section-label mb-3">Quick actions</h3>
            <div className="d-grid gap-2">
                {ACTIONS.map(action => (
                    <Link
                        key={action.href}
                        href={action.href}
                        className={action.primary ? 'btn btn-primary' : 'btn btn-outline-primary'}
                    >
                        <i className={`bi ${action.icon} me-2`} aria-hidden="true" />
                        {action.label}
                    </Link>
                ))}
            </div>
        </Card.Body>
    </Card>
)

export default AdminQuickActions
