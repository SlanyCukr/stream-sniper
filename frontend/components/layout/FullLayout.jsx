'use client'

import Sidebar from './Sidebar'
import Header from './Header'
import {
    Container,
} from 'react-bootstrap'

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
                className="sidebarArea shadow"
                id="sidebarArea"
                aria-label="Main navigation sidebar">
                <Sidebar />
            </aside>
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
                        className="p-4 wrapper"
                        fluid>
                        {children}
                    </Container>
                </main>
            </div>
        </div>
    </>
)

export default FullLayout
