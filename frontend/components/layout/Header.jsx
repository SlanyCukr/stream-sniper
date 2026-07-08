'use client'

import {
    useState,
} from 'react'
import {
    useRouter, usePathname,
} from 'next/navigation'
import {
    Dropdown,
    Button,
} from 'react-bootstrap'
import { useAuth } from '@/contexts/AuthContext'

/**
 * Admin menu items component
 */
const AdminMenuItems = ({ navigate }) => (
    <>
        <Dropdown.Divider role="separator" />
        <Dropdown.Item
            role="menuitem"
            tabIndex="0"
            onClick={() => navigate('/admin/dashboard')}
        >
            <i className="bi bi-speedometer2 me-2"></i>
            Admin Dashboard
        </Dropdown.Item>
        <Dropdown.Item
            role="menuitem"
            tabIndex="0"
            onClick={() => navigate('/admin/users')}
        >
            <i className="bi bi-person-gear me-2"></i>
            User Management
        </Dropdown.Item>
        <Dropdown.Item
            role="menuitem"
            tabIndex="0"
            onClick={() => navigate('/admin/system')}
        >
            <i className="bi bi-cpu me-2"></i>
            System Information
        </Dropdown.Item>
    </>
)

/**
 * User dropdown menu component
 */
const UserDropdown = ({
    user, dropdownOpen, toggle, handleProfile, handleLogout, navigate,
}) => (
    <Dropdown
        show={dropdownOpen}
        onToggle={toggle}
        align="end">
        <Dropdown.Toggle
            variant="dark"
            size="sm"
            aria-label="User menu"
            aria-expanded={dropdownOpen}
            aria-haspopup="true"
            className="user-chip"
        >
            <span
                className="avatar-orb"
                aria-hidden="true">
                {user?.username?.charAt(0) || '?'}
            </span>
            <span className="d-none d-md-inline">
                {user?.username}
            </span>
            {user?.role === 'admin' && (
                <span className="role-chip d-none d-md-inline">
                    Admin
                </span>
            )}
        </Dropdown.Toggle>
        <Dropdown.Menu
            role="menu"
            aria-label="User account options">
            <Dropdown.Header role="presentation">
                {user?.username}
                <br />
                <small className="text-muted">{user?.email}</small>
            </Dropdown.Header>
            <Dropdown.Item
                role="menuitem"
                tabIndex="0"
                onClick={handleProfile}>
                <i className="bi bi-person me-2"></i>
                My Profile
            </Dropdown.Item>
            {user?.role === 'admin' && <AdminMenuItems navigate={navigate} />}
            <Dropdown.Divider role="separator" />
            <Dropdown.Item
                role="menuitem"
                tabIndex="0"
                onClick={handleLogout}>
                <i className="bi bi-box-arrow-right me-2"></i>
                Logout
            </Dropdown.Item>
        </Dropdown.Menu>
    </Dropdown>
)

/**
 * Mobile sidebar toggle button
 */
const MobileSidebarToggle = ({
    showMobilemenu, handleKeyDown,
}) => (
    <Button
        variant="outline-primary"
        size="sm"
        className="d-lg-none"
        onClick={() => showMobilemenu()}
        onKeyDown={e => handleKeyDown(e, showMobilemenu)}
        aria-label="Open navigation menu"
        aria-expanded="false"
    >
        <i
            className="bi bi-list"
            aria-hidden="true"></i>
    </Button>
)

/** Mono breadcrumb-style readout of the current route. */
const HeaderPath = ({ pathname }) => {
    const segments = pathname === '/'
        ? [
            'streams',
        ]
        : pathname.split('/').filter(Boolean)

    return (
        <span
            className="header-path d-none d-sm-inline"
            aria-hidden="true">
            ~
            {segments.map((segment, index) => (
                <span key={index}>
                    <span className="path-sep">/</span>
                    <span className={index === segments.length - 1 ? 'path-current' : ''}>
                        {segment}
                    </span>
                </span>
            ))}
        </span>
    )
}

const Header = () => {
    const [
        dropdownOpen,
        setDropdownOpen,
    ] = useState(false)
    const {
        isAuthenticated, user, logout,
    } = useAuth()
    const router = useRouter()
    const pathname = usePathname()

    const toggle = () => setDropdownOpen(prevState => !prevState)
    const showMobilemenu = () => {
        document.getElementById('sidebarArea').classList.toggle('showSidebar')
    }

    const handleLogout = () => {
        logout()
        router.push('/login')
    }

    const handleLogin = () => router.push('/login')
    const handleProfile = () => router.push('/profile')

    // Handle keyboard navigation
    const handleKeyDown = (event, action) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            action()
        }
    }

    return (
        <header
            className="appHeader d-flex align-items-center justify-content-between"
            role="navigation"
            aria-label="Main header navigation"
        >
            <div className="d-flex align-items-center gap-3">
                <MobileSidebarToggle
                    showMobilemenu={showMobilemenu}
                    handleKeyDown={handleKeyDown}
                />
                <HeaderPath pathname={pathname} />
            </div>

            <div className="d-flex align-items-center gap-2">
                {isAuthenticated ? (
                    <UserDropdown
                        user={user}
                        dropdownOpen={dropdownOpen}
                        toggle={toggle}
                        handleProfile={handleProfile}
                        handleLogout={handleLogout}
                        navigate={router.push}
                    />
                ) : (
                    <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={handleLogin}
                        aria-label="Login to your account"
                    >
                        <i className="bi bi-box-arrow-in-right me-2"></i>
                        Login
                    </Button>
                )}
            </div>
        </header>
    )
}

export default Header
