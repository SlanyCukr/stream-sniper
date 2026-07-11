'use client'

import {
    Button, Nav,
} from 'react-bootstrap'
import Logo from './Logo'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

const navigation = [
    {
        title: 'All streams',
        href: '/',
        icon: 'bi bi-collection-play',
    },
    {
        title: 'Chatter explorer',
        href: '/chatter',
        icon: 'bi bi-fingerprint',
    },
    {
        title: 'Creators',
        href: '/regulars',
        icon: 'bi bi-people',
    },
]

const adminNavigation = [
    {
        title: 'Dashboard',
        href: '/admin/dashboard',
        icon: 'bi bi-speedometer2',
    },
    {
        title: 'Users',
        href: '/admin/users',
        icon: 'bi bi-person-gear',
    },
    {
        title: 'Tracking',
        href: '/admin/tracking',
        icon: 'bi bi-broadcast',
    },
    {
        title: 'System',
        href: '/admin/system',
        icon: 'bi bi-cpu',
    },
]

/** Active when the path matches exactly, or is nested under a non-root href. */
const isActivePath = (pathname, href) => {
    if (href === '/') {
        return pathname === '/'
    }
    return pathname === href || pathname.startsWith(`${href}/`)
}

const NavLinks = ({
    items, pathname, keyPrefix,
}) => items.map((navi, index) => (
    <Nav.Item
        key={`${keyPrefix}${index}`}
        role="none"
    >
        <Link
            href={navi.href}
            className={
                isActivePath(pathname, navi.href)
                    ? 'nav-link active'
                    : 'nav-link'
            }
            aria-current={isActivePath(pathname, navi.href) ? 'page' : null}
            aria-label={navi.title}
        >
            <i
                className={navi.icon}
                aria-hidden="true"
            ></i>
            <span className="ms-3 d-inline-block">{navi.title}</span>
        </Link>
    </Nav.Item>
))

const Sidebar = () => {
    const {
        isAuthenticated, isAdmin,
    } = useAuth()

    const showMobilemenu = () => {
        document.getElementById('sidebarArea').classList.toggle('showSidebar')
    }

    // Handle keyboard navigation for mobile menu
    const handleMobileMenuKeyDown = event => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            showMobilemenu()
        }
        if (event.key === 'Escape') {
            // Close mobile menu if open
            const sidebarArea = document.getElementById('sidebarArea')
            if (sidebarArea?.classList.contains('showSidebar')) {
                showMobilemenu()
            }
        }
    }

    const pathname = usePathname()

    return (
        <div className="sidebar-inner p-3 pb-0">
            <div className="d-flex align-items-center">
                <Logo />
                <Button
                    variant="close"
                    size="sm"
                    className="ms-auto d-lg-none"
                    onClick={() => showMobilemenu()}
                    onKeyDown={handleMobileMenuKeyDown}
                    aria-label="Close navigation menu"
                    aria-expanded="true"
                />
            </div>
            <nav
                className="pt-4 mt-2 flex-grow-1 d-flex flex-column"
                aria-label="Main navigation">
                <Nav
                    className="flex-column sidebarNav"
                    role="navigation"
                >
                    <div className="px-3 pb-1">
                        <span className="sidebar-section">Intel</span>
                    </div>
                    <NavLinks
                        items={navigation}
                        pathname={pathname}
                        keyPrefix=""
                    />

                    {/* Admin Navigation */}
                    {isAuthenticated && isAdmin && (
                        <>
                            <hr className="my-3" />
                            <div className="px-3 pb-1">
                                <span className="sidebar-section">Command</span>
                            </div>
                            <NavLinks
                                items={adminNavigation}
                                pathname={pathname}
                                keyPrefix="admin-"
                            />
                        </>
                    )}
                </Nav>
            </nav>
            <div
                className="sidebar-status"
                aria-hidden="true"
            >
                <span className="status-dot"></span>
                <span>Link active</span>
            </div>
        </div>
    )
}

export default Sidebar
