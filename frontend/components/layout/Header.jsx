'use client'

import {
    useState,
} from 'react'
import {
    useRouter,
} from 'next/navigation'
import {
    Navbar,
    Nav,
    Dropdown,
    Button,
    Badge,
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
            <i className="bi bi-shield-check me-2"></i>
            Admin Dashboard
        </Dropdown.Item>
        <Dropdown.Item
            role="menuitem"
            tabIndex="0"
            onClick={() => navigate('/admin/users')}
        >
            <i className="bi bi-people me-2"></i>
            User Management
        </Dropdown.Item>
        <Dropdown.Item
            role="menuitem"
            tabIndex="0"
            onClick={() => navigate('/admin/system')}
        >
            <i className="bi bi-gear me-2"></i>
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
        onToggle={toggle}>
        <Dropdown.Toggle
            variant="primary"
            aria-label="User menu"
            aria-expanded={dropdownOpen}
            aria-haspopup="true"
            className="d-flex align-items-center"
        >
            <img
                src="/images/user1.jpg"
                alt="User profile picture"
                className="rounded-circle me-2"
                width="30"
            />
            <span className="d-none d-md-inline">
                {user?.username}
            </span>
            {user?.role === 'admin' && (
                <Badge
                    bg="warning"
                    className="ms-2">
                    Admin
                </Badge>
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
 * Mobile navigation toggle button
 */
const MobileNavToggle = ({
    isOpen, Handletoggle, handleKeyDown,
}) => (
    <Button
        variant="primary"
        size="sm"
        className="d-sm-block d-md-none"
        onClick={Handletoggle}
        onKeyDown={e => handleKeyDown(e, Handletoggle)}
        aria-label={isOpen ? 'Close menu' : 'Open menu'}
        aria-expanded={isOpen}
    >
        {isOpen ? (
            <i
                className="bi bi-x"
                aria-hidden="true"></i>
        ) : (
            <i
                className="bi bi-three-dots-vertical"
                aria-hidden="true"></i>
        )}
    </Button>
)

/**
 * Mobile sidebar toggle button
 */
const MobileSidebarToggle = ({
    showMobilemenu, handleKeyDown,
}) => (
    <Button
        variant="primary"
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

const Header = () => {
    const [
        isOpen,
        setIsOpen,
    ] = useState(false)
    const [
        dropdownOpen,
        setDropdownOpen,
    ] = useState(false)
    const {
        isAuthenticated, user, logout,
    } = useAuth()
    const router = useRouter()

    const toggle = () => setDropdownOpen(prevState => !prevState)
    const Handletoggle = () => setIsOpen(!isOpen)
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
        <Navbar
            bg="primary"
            variant="dark"
            expand="md"
            role="navigation"
            aria-label="Main header navigation"
        >
            <div className="d-flex align-items-center">
                <Navbar.Brand
                    href="/"
                    className="d-lg-none"
                    aria-label="Stream Sniper - Home"
                >
                    <img
                        src="/images/xtremelogowhite.svg"
                        alt="Stream Sniper"
                    />
                </Navbar.Brand>
                <MobileSidebarToggle
                    showMobilemenu={showMobilemenu}
                    handleKeyDown={handleKeyDown}
                />
            </div>

            <div className="hstack gap-2">
                <MobileNavToggle
                    isOpen={isOpen}
                    Handletoggle={Handletoggle}
                    handleKeyDown={handleKeyDown}
                />
            </div>

            <Navbar.Collapse
                in={isOpen}
                role="region"
                aria-label="Navigation menu">
                <Nav className="me-auto">
                    {/* Navigation links can be added here */}
                </Nav>

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
                        variant="outline-light"
                        onClick={handleLogin}
                        aria-label="Login to your account"
                    >
                        <i className="bi bi-box-arrow-in-right me-2"></i>
                        Login
                    </Button>
                )}
            </Navbar.Collapse>
        </Navbar>
    )
}

export default Header
