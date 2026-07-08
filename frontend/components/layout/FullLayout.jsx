'use client'

import Sidebar from './Sidebar'
import Header from './Header'
import {
    Container,
} from 'react-bootstrap'

/** Closes the mobile sidebar when the dimmed backdrop is tapped. */
const closeMobileSidebar = () => {
    document.getElementById('sidebarArea')?.classList.remove('showSidebar')
}

const FullLayout = ({ children }) => (
    <>
        {/* Skip link for keyboard navigation */}
        <a
            href="#main-content"
            className="skip-link"
            aria-label="Skip to main content"
        >
            Skip to main content
        </a>
        <div className="pageWrapper d-lg-flex">
            {/********Sidebar**********/}
            <aside
                className="sidebarArea"
                id="sidebarArea"
                aria-label="Main navigation sidebar">
                <Sidebar />
            </aside>
            {/* mobile-only dimmed backdrop; visible while the sidebar is open */}
            <div
                className="sidebar-backdrop d-lg-none"
                onClick={closeMobileSidebar}
                aria-hidden="true"
            />
            {/********Content Area**********/}

            <div className="contentArea">
                {/********header**********/}
                <Header />
                {/********Middle Content**********/}
                <main
                    id="main-content"
                    aria-label="Main content area"
                >
                    <Container
                        className="p-3 p-md-4 wrapper"
                        fluid>
                        {children}
                    </Container>
                </main>
            </div>
        </div>
    </>
)

export default FullLayout
