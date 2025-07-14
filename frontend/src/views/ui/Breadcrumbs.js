import {
    Row, Col, Card, Breadcrumb,
} from 'react-bootstrap'

const Breadcrumbs = () => (
    <Row>
        <Col>
            {/* --------------------------------------------------------------------------------*/}
            {/* Card-1*/}
            {/* --------------------------------------------------------------------------------*/}
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-link me-2"> </i>
            Basic Breadcrumbs
                </Card.Title>
                <Card.Body className="">
                    <Breadcrumb>
                        <Breadcrumb.Item active>Home</Breadcrumb.Item>
                    </Breadcrumb>
                    <Breadcrumb>
                        <Breadcrumb.Item>
                            <a href="/">Home</a>
                        </Breadcrumb.Item>
                        <Breadcrumb.Item active>Library</Breadcrumb.Item>
                    </Breadcrumb>
                    <Breadcrumb>
                        <Breadcrumb.Item>
                            <a href="/">Home</a>
                        </Breadcrumb.Item>
                        <Breadcrumb.Item>
                            <a href="/">Library</a>
                        </Breadcrumb.Item>
                        <Breadcrumb.Item active>Data</Breadcrumb.Item>
                    </Breadcrumb>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default Breadcrumbs
