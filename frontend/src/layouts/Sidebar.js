import {
    Button, Nav,
} from 'react-bootstrap'
import Logo from './Logo'
import {
    Link, useLocation,
} from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const navigation = [
    {
        title: 'Dashboard',
        href: '/starter',
        icon: 'bi bi-speedometer2',
    },
    {
        title: 'All streams',
        href: '/all-streams',
        icon: 'bi bi-person',
    },
    {
        title: 'Get chatter messages',
        href: '/chatter-messages',
        icon: 'bi bi-person',
    },
    // {
    //     title: 'Alert',
    //     href: '/alerts',
    //     icon: 'bi bi-bell',
    // },
    // {
    //     title: 'Badges',
    //     href: '/badges',
    //     icon: 'bi bi-patch-check',
    // },
    // {
    //     title: 'Buttons',
    //     href: '/buttons',
    //     icon: 'bi bi-hdd-stack',
    // },
    // {
    //     title: 'Cards',
    //     href: '/cards',
    //     icon: 'bi bi-card-text',
    // },
    // {
    //     title: 'Grid',
    //     href: '/grid',
    //     icon: 'bi bi-columns',
    // },
    // {
    //     title: 'Table',
    //     href: '/table',
    //     icon: 'bi bi-layout-split',
    // },
    // {
    //     title: 'Forms',
    //     href: '/forms',
    //     icon: 'bi bi-textarea-resize',
    // },
    // {
    //     title: 'Breadcrumbs',
    //     href: '/breadcrumbs',
    //     icon: 'bi bi-link',
    // },
    // {
    //     title: 'About',
    //     href: '/about',
    //     icon: 'bi bi-people',
    // },
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
    const { isAuthenticated, isAdmin } = useAuth()
    
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

    let location = useLocation()

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
                                to={navi.href}
                                className={
                                    location.pathname === navi.href
                                        ? 'text-primary nav-link py-3'
                                        : 'nav-link text-secondary py-3'
                                }
                                aria-current={location.pathname === navi.href ? 'page' : null}
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
                            <div className="px-3">
                                <small className="text-muted text-uppercase">Administration</small>
                            </div>
                            {adminNavigation.map((navi, index) => (
                                <Nav.Item
                                    key={`admin-${index}`}
                                    className="sidenav-bg"
                                    role="none"
                                >
                                    <Link
                                        to={navi.href}
                                        className={
                                            location.pathname === navi.href
                                                ? 'text-primary nav-link py-3'
                                                : 'nav-link text-secondary py-3'
                                        }
                                        aria-current={location.pathname === navi.href ? 'page' : null}
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
                    {/* <Button
                        color="danger"
                        tag="a"
                        target="_blank"
                        className="mt-3"
                        href="https://www.wrappixel.com/templates/xtreme-react-redux-admin/?ref=33"
                    >
            Upgrade To Pro
                    </Button> */}
                </Nav>
            </nav>
        </div>
    )
}

export default Sidebar
