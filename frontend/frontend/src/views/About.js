import {
    Row,
    Col,
    Card,
    Button,
} from 'react-bootstrap'

const About = () => (
    <main>
        <Row>
            <Col>
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-1*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card>
                    <Card.Header>
                        <h1 className="border-bottom p-3 mb-0">
                            <i
                                className="bi bi-bell me-2"
                                aria-hidden="true">
                            </i>
                            About Xtreme React
                        </h1>
                    </Card.Header>
                    <Card.Body className="p-4">
                        <Row justify-content>
                            <Col lg="8">
                                <h2 className="mt-4">Xtreme React Admin Pro Version</h2>
                                <h5 className=" mb-4">
                                    5 premium and highly customizable demo variations included in
                                    the package, with React Router 6, Redux Toolkit, Axios nd much
                                    more...
                                </h5>
                                <img
                                    src="https://www.wrappixel.com/wp-content/uploads/edd/2020/04/xtreme-react-admin-template-y.jpg"
                                    alt="my"
                                />
                                <Button
                                    className="mt-3"
                                    variant="primary"
                                    href="https://www.wrappixel.com/templates/xtreme-react-redux-admin/?ref=33"
                                    target="_blank"
                                >
                                    Check Pro Version
                                </Button>
                            </Col>
                        </Row>
                    </Card.Body>
                </Card>
            </Col>
        </Row>
    </main>
)

export default About
