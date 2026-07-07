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
        icon: 'bi bi-person',
    },
    {
        title: 'Get chatter messages',
        href: '/chatter-messages',
        icon: 'bi bi-person',
    },
]

const adminNavigation = [
    {
        title: 'Admin Dashboard',
        href: '/admin/dashboard',
        icon: 'bi bi-shield-check',
    },
    {
        title: 'User Management',
        href: '/admin/users',
        icon: 'bi bi-people',
    },
    {
        title: 'System Information',
        href: '/admin/system',
        icon: 'bi bi-gear',
    },
]

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
        <div className="p-3">
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
                className="pt-4 mt-2"
                aria-label="Main navigation">
                <Nav
                    className="flex-column sidebarNav"
                    role="navigation"
                >
                    {navigation.map((navi, index) => (
                        <Nav.Item
                            key={index}
                            className="sidenav-bg"
                            role="none"
                        >
                            <Link
                                href={navi.href}
                                className={
                                    pathname === navi.href
                                        ? 'nav-link active'
                                        : 'nav-link'
                                }
                                aria-current={pathname === navi.href ? 'page' : null}
                                aria-label={navi.title}
                            >
                                <i
                                    className={navi.icon}
                                    aria-hidden="true"
                                ></i>
                                <span className="ms-3 d-inline-block">{navi.title}</span>
                            </Link>
                        </Nav.Item>
                    ))}

                    {/* Admin Navigation */}
                    {isAuthenticated && isAdmin && (
                        <>
                            <hr className="my-3" />
                            <div className="px-3 pb-1">
                                <span className="sidebar-section">// Administration</span>
                            </div>
                            {adminNavigation.map((navi, index) => (
                                <Nav.Item
                                    key={`admin-${index}`}
                                    className="sidenav-bg"
                                    role="none"
                                >
                                    <Link
                                        href={navi.href}
                                        className={
                                            pathname === navi.href
                                                ? 'text-primary nav-link py-3'
                                                : 'nav-link text-secondary py-3'
                                        }
                                        aria-current={pathname === navi.href ? 'page' : null}
                                        aria-label={navi.title}
                                    >
                                        <i
                                            className={navi.icon}
                                            aria-hidden="true"
                                        ></i>
                                        <span className="ms-3 d-inline-block">{navi.title}</span>
                                    </Link>
                                </Nav.Item>
                            ))}
                        </>
                    )}
                </Nav>
            </nav>
        </div>
    )
}

export default Sidebar
