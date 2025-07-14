import React from 'react'
import { Link } from 'react-router-dom'
import {
    Navbar,
    Nav,
    Dropdown,
    Button,
} from 'react-bootstrap'
import { ReactComponent as LogoWhite } from '../assets/images/logos/xtremelogowhite.svg'
import user1 from '../assets/images/users/user1.jpg'

const Header = () => {
    const [
        isOpen,
        setIsOpen,
    ] = React.useState(false)
    const [
        dropdownOpen,
        setDropdownOpen,
    ] = React.useState(false)

    const toggle = () => setDropdownOpen(prevState => !prevState)
    const Handletoggle = () => {
        setIsOpen(!isOpen)
    }
    const showMobilemenu = () => {
        document.getElementById('sidebarArea').classList.toggle('showSidebar')
    }

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
                    aria-label="Stream Sniper - Home">
                    <LogoWhite />
                </Navbar.Brand>
                <Button
                    color="primary"
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
            </div>
            <div className="hstack gap-2">
                <Button
                    color="primary"
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
            </div>

            <Navbar.Collapse
                in={isOpen}
                role="region"
                aria-label="Navigation menu">
                {/* <Nav
                    className="me-auto"
                    navbar>
                    <NavItem>
                        <Link
                            to="/starter"
                            className="nav-link">
              Starter
                        </Link>
                    </NavItem>
                    <NavItem>
                        <Link
                            to="/about"
                            className="nav-link">
              About
                        </Link>
                    </NavItem>
                    <UncontrolledDropdown
                        inNavbar
                        nav>
                        <DropdownToggle
                            caret
                            nav>
              DD Menu
                        </DropdownToggle>
                        <DropdownMenu end>
                            <DropdownItem>Option 1</DropdownItem>
                            <DropdownItem>Option 2</DropdownItem>
                            <DropdownItem divider />
                            <DropdownItem>Reset</DropdownItem>
                        </DropdownMenu>
                    </UncontrolledDropdown>
                </Nav> */}
                <Dropdown
                    isOpen={dropdownOpen}
                    toggle={toggle}
                >
                    <Dropdown.Toggle
                        variant="primary"
                        aria-label="User menu"
                        aria-expanded={dropdownOpen}
                        aria-haspopup="true"
                    >
                        <img
                            src={user1}
                            alt="User profile picture"
                            className="rounded-circle"
                            width="30"
                        ></img>
                    </Dropdown.Toggle>
                    <Dropdown.Menu
                        role="menu"
                        aria-label="User account options">
                        <Dropdown.Header role="presentation">Info</Dropdown.Header>
                        <Dropdown.Item
                            role="menuitem"
                            tabIndex="0">My Account</Dropdown.Item>
                        <Dropdown.Item
                            role="menuitem"
                            tabIndex="0">Edit Profile</Dropdown.Item>
                        <Dropdown.Divider role="separator" />
                        <Dropdown.Item
                            role="menuitem"
                            tabIndex="0">My Balance</Dropdown.Item>
                        <Dropdown.Item
                            role="menuitem"
                            tabIndex="0">Inbox</Dropdown.Item>
                        <Dropdown.Item
                            role="menuitem"
                            tabIndex="0">Logout</Dropdown.Item>
                    </Dropdown.Menu>
                </Dropdown>
            </Navbar.Collapse>
        </Navbar>
    )
}

export default Header
