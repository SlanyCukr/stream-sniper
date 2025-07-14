import {
    Badge, Button, Card, Row, Col,
} from 'react-bootstrap'

const Badges = () => (
    <div>
        {/* --------------------------------------------------------------------------------*/}
        {/* Row*/}
        {/* --------------------------------------------------------------------------------*/}
        <Row>
            <Col
                xs="12"
                md="12"
                sm="12">
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-1*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card>
                    <Card.Title
                        as="h6"
                        className="border-bottom p-3 mb-0">
              Badges
                    </Card.Title>
                    <Card.Body className="">
                        <div>
                            <h1>
                  Heading <Badge variant="secondary">New</Badge>
                            </h1>
                            <h2>
                  Heading <Badge variant="secondary">New</Badge>
                            </h2>
                            <h3>
                  Heading <Badge variant="secondary">New</Badge>
                            </h3>
                            <h4>
                  Heading <Badge variant="secondary">New</Badge>
                            </h4>
                            <h5>
                  Heading <Badge variant="secondary">New</Badge>
                            </h5>
                            <h6>
                  Heading <Badge variant="secondary">New</Badge>
                            </h6>
                        </div>
                    </Card.Body>
                </Card>
            </Col>
            <Col
                xs="12"
                md="12"
                sm="12">
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-2*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card>
                    <Card.Title
                        as="h6"
                        className="border-bottom p-3 mb-0">
              Badges with Button
                    </Card.Title>
                    <Card.Body className="">
                        <div>
                            <Button
                                variant="primary"
                                outline>
                  Notifications <Badge variant="secondary">1</Badge>
                            </Button>
                            <Button
                                variant="secondary"
                                className="ms-3"
                                outline>
                  Notifications <Badge variant="secondary">2</Badge>
                            </Button>
                            <Button
                                variant="info"
                                className="ms-3"
                                outline>
                  Notifications <Badge variant="secondary">3</Badge>
                            </Button>
                            <Button
                                variant="warning"
                                className="ms-3"
                                outline>
                  Notifications <Badge variant="secondary">4</Badge>
                            </Button>
                            <Button
                                variant="danger"
                                className="ms-3"
                                outline>
                  Notifications <Badge variant="secondary">5</Badge>
                            </Button>
                        </div>
                    </Card.Body>
                </Card>
            </Col>
            <Col
                xs="12"
                md="6">
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-3*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card>
                    <Card.Title
                        as="h6"
                        className="border-bottom p-3 mb-0">
              Badges with Contextual variations
                    </Card.Title>
                    <Card.Body className="">
                        <div>
                            <Badge variant="primary">Primary</Badge>
                            <Badge
                                variant="secondary"
                                className="ms-3">
                  Secondary
                            </Badge>
                            <Badge
                                variant="success"
                                className="ms-3">
                  Success
                            </Badge>
                            <Badge
                                variant="danger"
                                className="ms-3">
                  Danger
                            </Badge>
                            <Badge
                                variant="warning"
                                className="ms-3">
                  Warning
                            </Badge>
                            <Badge
                                variant="info"
                                className="ms-3">
                  Info
                            </Badge>
                            <Badge
                                variant="light"
                                className="ms-3">
                  Light
                            </Badge>
                            <Badge
                                variant="dark"
                                className="ms-3">
                  Dark
                            </Badge>
                        </div>
                    </Card.Body>
                </Card>
            </Col>
            <Col
                xs="12"
                md="6">
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-4*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card>
                    <Card.Title
                        as="h6"
                        className="border-bottom p-3 mb-0">
              Badges with Pills
                    </Card.Title>
                    <Card.Body className="">
                        <div>
                            <Badge
                                variant="primary"
                                pill>
                  Primary
                            </Badge>
                            <Badge
                                variant="secondary"
                                className="ms-3"
                                pill>
                  Secondary
                            </Badge>
                            <Badge
                                variant="success"
                                className="ms-3"
                                pill>
                  Success
                            </Badge>
                            <Badge
                                variant="danger"
                                className="ms-3"
                                pill>
                  Danger
                            </Badge>
                            <Badge
                                variant="warning"
                                className="ms-3"
                                pill>
                  Warning
                            </Badge>
                            <Badge
                                variant="info"
                                className="ms-3"
                                pill>
                  Info
                            </Badge>
                            <Badge
                                variant="light"
                                className="ms-3"
                                pill>
                  Light
                            </Badge>
                            <Badge
                                variant="dark"
                                className="ms-3"
                                pill>
                  Dark
                            </Badge>
                        </div>
                    </Card.Body>
                </Card>
            </Col>
            <Col
                xs="12"
                md="6">
                {/* --------------------------------------------------------------------------------*/}
                {/* Card-5*/}
                {/* --------------------------------------------------------------------------------*/}
                <Card>
                    <Card.Title
                        as="h6"
                        className="border-bottom p-3 mb-0">
              Badges with Links
                    </Card.Title>
                    <Card.Body className="">
                        <div>
                            <Badge
                                href=""
                                variant="primary">
                  Primary
                            </Badge>
                            <Badge
                                href=""
                                variant="secondary"
                                className="ms-3">
                  Secondary
                            </Badge>
                            <Badge
                                href=""
                                variant="success"
                                className="ms-3">
                  Success
                            </Badge>
                            <Badge
                                href=""
                                variant="danger"
                                className="ms-3">
                  Danger
                            </Badge>
                            <Badge
                                href=""
                                variant="warning"
                                className="ms-3">
                  Warning
                            </Badge>
                            <Badge
                                href=""
                                variant="info"
                                className="ms-3">
                  Info
                            </Badge>
                            <Badge
                                href=""
                                variant="light"
                                className="ms-3">
                  Light
                            </Badge>
                            <Badge
                                href=""
                                variant="dark"
                                className="ms-3">
                  Dark
                            </Badge>
                        </div>
                    </Card.Body>
                </Card>
            </Col>
        </Row>
        {/* --------------------------------------------------------------------------------*/}
        {/* Row*/}
        {/* --------------------------------------------------------------------------------*/}
    </div>
)

export default Badges
