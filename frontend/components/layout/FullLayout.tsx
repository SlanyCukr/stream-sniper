'use client'

import { useState, type ReactNode } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import {
    Container,
} from 'react-bootstrap'

interface FullLayoutProps {
    children: ReactNode
}

const FullLayout = ({ children }: FullLayoutProps) => {
    const [isSidebarOpen, setSidebarOpen] = useState(false)
    const closeSidebar = () => setSidebarOpen(false)

    return (
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
            <aside
                className={`sidebarArea${isSidebarOpen ? ' showSidebar' : ''}`}
                id="sidebarArea"
                aria-label="Main navigation sidebar">
                <Sidebar
                    isSidebarOpen={isSidebarOpen}
                    onCloseSidebar={closeSidebar} />
            </aside>
            {/* mobile-only dimmed backdrop; visible while the sidebar is open */}
            <div
                className="sidebar-backdrop d-lg-none"
                onClick={closeSidebar}
                data-open={String(isSidebarOpen)}
                aria-hidden="true"
            />
            <div className="contentArea">
                <Header
                    isSidebarOpen={isSidebarOpen}
                    onToggleSidebar={() => setSidebarOpen(open => !open)} />
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
}

export default FullLayout
