import React, {
    Suspense, lazy,
} from 'react'
import {
    Col,
    Row,
    Spinner,
} from 'react-bootstrap'

// Lazy load heavy dashboard components
const SalesChart = lazy(() => import('../components/dashboard/SalesChart'))
const Feeds = lazy(() => import('../components/dashboard/Feeds'))
const ProjectTables = lazy(() => import('../components/dashboard/ProjectTable'))
const TopCards = lazy(() => import('../components/dashboard/TopCards'))
const Blog = lazy(() => import('../components/dashboard/Blog'))
import bg1 from '../assets/images/bg/bg1.jpg'
import bg2 from '../assets/images/bg/bg2.jpg'
import bg3 from '../assets/images/bg/bg3.jpg'
import bg4 from '../assets/images/bg/bg4.jpg'

const BlogData = [
    {
        image: bg1,
        title: 'This is simple blog',
        subtitle: '2 comments, 1 Like',
        description:
            'This is a wider card with supporting text below as a natural lead-in to additional content.',
        btnbg: 'primary',
    },
    {
        image: bg2,
        title: 'Lets be simple blog',
        subtitle: '2 comments, 1 Like',
        description:
            'This is a wider card with supporting text below as a natural lead-in to additional content.',
        btnbg: 'primary',
    },
    {
        image: bg3,
        title: "Don't Lamp blog",
        subtitle: '2 comments, 1 Like',
        description:
            'This is a wider card with supporting text below as a natural lead-in to additional content.',
        btnbg: 'primary',
    },
    {
        image: bg4,
        title: 'Simple is beautiful',
        subtitle: '2 comments, 1 Like',
        description:
            'This is a wider card with supporting text below as a natural lead-in to additional content.',
        btnbg: 'primary',
    },
]

const Starter = () => (
    <main>
        {/* Page heading */}
        <div className="visually-hidden">
            <h1>Dashboard</h1>
        </div>

        {/***Top Cards***/}
        <section aria-labelledby="metrics-heading">
            <h2
                id="metrics-heading"
                className="visually-hidden">
                Key Metrics
            </h2>
            <Suspense fallback={<div className="d-flex justify-content-center p-4"><Spinner animation="border" /></div>}>
                <Row>
                    <Col
                        sm="6"
                        lg="3">
                        <TopCards
                            bg="bg-light-success text-success"
                            title="Profit"
                            subtitle="Yearly Earning"
                            earning="$21k"
                            icon="bi bi-wallet"
                        />
                    </Col>
                    <Col
                        sm="6"
                        lg="3">
                        <TopCards
                            bg="bg-light-danger text-danger"
                            title="Refunds"
                            subtitle="Refund given"
                            earning="$1k"
                            icon="bi bi-coin"
                        />
                    </Col>
                    <Col
                        sm="6"
                        lg="3">
                        <TopCards
                            bg="bg-light-warning text-warning"
                            title="New Project"
                            subtitle="Yearly Project"
                            earning="456"
                            icon="bi bi-basket3"
                        />
                    </Col>
                    <Col
                        sm="6"
                        lg="3">
                        <TopCards
                            bg="bg-light-info text-into"
                            title="Sales"
                            subtitle="Weekly Sales"
                            earning="210"
                            icon="bi bi-bag"
                        />
                    </Col>
                </Row>
            </Suspense>
        </section>

        {/***Sales & Feed***/}
        <section aria-labelledby="analytics-heading">
            <h2
                id="analytics-heading"
                className="visually-hidden">
                Analytics and Feeds
            </h2>
            <Row>
                <Col
                    sm="6"
                    lg="6"
                    xl="7"
                    xxl="8">
                    <Suspense fallback={<div className="d-flex justify-content-center p-4"><Spinner animation="border" /></div>}>
                        <SalesChart />
                    </Suspense>
                </Col>
                <Col
                    sm="6"
                    lg="6"
                    xl="5"
                    xxl="4">
                    <Suspense fallback={<div className="d-flex justify-content-center p-4"><Spinner animation="border" /></div>}>
                        <Feeds />
                    </Suspense>
                </Col>
            </Row>
        </section>

        {/***Table ***/}
        <section aria-labelledby="projects-heading">
            <h2
                id="projects-heading"
                className="visually-hidden">
                Project Table
            </h2>
            <Row>
                <Col lg="12">
                    <Suspense fallback={<div className="d-flex justify-content-center p-4"><Spinner animation="border" /></div>}>
                        <ProjectTables />
                    </Suspense>
                </Col>
            </Row>
        </section>

        {/***Blog Cards***/}
        <section aria-labelledby="blog-heading">
            <h2
                id="blog-heading"
                className="visually-hidden">
                Blog Articles
            </h2>
            <Suspense fallback={<div className="d-flex justify-content-center p-4"><Spinner animation="border" /></div>}>
                <Row>
                    {BlogData.map((blg, index) => (
                        <Col
                            sm="6"
                            lg="6"
                            xl="3"
                            key={index}>
                            <Blog
                                image={blg.image}
                                title={blg.title}
                                subtitle={blg.subtitle}
                                text={blg.description}
                                color={blg.btnbg}
                            />
                        </Col>
                    ))}
                </Row>
            </Suspense>
        </section>
    </main>
)

export default Starter
