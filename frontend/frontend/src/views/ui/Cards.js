/* eslint-disable max-lines */
import {
    Card, CardGroup, Button, Row, Col,
} from 'react-bootstrap'
import Blog from '../../components/dashboard/Blog'
import bg1 from '../../assets/images/bg/bg1.jpg'
import bg2 from '../../assets/images/bg/bg2.jpg'
import bg3 from '../../assets/images/bg/bg3.jpg'
import bg4 from '../../assets/images/bg/bg4.jpg'

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

const Cards = () => (
    <div>
        {/* --------------------------------------------------------------------------------*/}
        {/* Card-1*/}
        {/* --------------------------------------------------------------------------------*/}
        <h5 className="mb-3">Basic Card</h5>
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
        {/* --------------------------------------------------------------------------------*/}
        {/* Card-2*/}
        {/* --------------------------------------------------------------------------------*/}
        <Row>
            <h5 className="mb-3 mt-3">Alignment Text</h5>
            <Col
                md="6"
                lg="4">
                <Card body>
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button color="light-warning">Go somewhere</Button>
                    </div>
                </Card>
            </Col>
            <Col
                md="6"
                lg="4">
                <Card
                    body
                    className="text-center">
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button color="light-danger">Go somewhere</Button>
                    </div>
                </Card>
            </Col>
            <Col
                md="6"
                lg="4">
                <Card
                    body
                    className="text-end">
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button color="light-success">Go somewhere</Button>
                    </div>
                </Card>
            </Col>
        </Row>
        {/* --------------------------------------------------------------------------------*/}
        {/* Card-2*/}
        {/* --------------------------------------------------------------------------------*/}
        <Row>
            <h5 className="mb-3 mt-3">Colored Card</h5>
            <Col
                md="6"
                lg="3">
                <Card
                    body
                    variant="primary"
                    inverse>
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button>Button</Button>
                    </div>
                </Card>
            </Col>
            <Col
                md="6"
                lg="3">
                <Card
                    body
                    variant="info"
                    inverse>
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button>Button</Button>
                    </div>
                </Card>
            </Col>
            <Col
                md="6"
                lg="3">
                <Card
                    body
                    variant="success"
                    inverse>
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button>Button</Button>
                    </div>
                </Card>
            </Col>
            <Col
                md="6"
                lg="3">
                <Card
                    body
                    variant="danger"
                    inverse>
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button>Button</Button>
                    </div>
                </Card>
            </Col>
            <Col
                md="6"
                lg="3">
                <Card
                    body
                    color="light-warning">
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button>Button</Button>
                    </div>
                </Card>
            </Col>
            <Col
                md="6"
                lg="3">
                <Card
                    body
                    color="light-info">
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button>Button</Button>
                    </div>
                </Card>
            </Col>
            <Col
                md="6"
                lg="3">
                <Card
                    body
                    color="light-success">
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button>Button</Button>
                    </div>
                </Card>
            </Col>
            <Col
                md="6"
                lg="3">
                <Card
                    body
                    color="light-danger">
                    <Card.Title as="h5">Special Title Treatment</Card.Title>
                    <Card.Text>
              With supporting text below as a natural lead-in to additional
              content.
                    </Card.Text>
                    <div>
                        <Button>Button</Button>
                    </div>
                </Card>
            </Col>
        </Row>
        {/* --------------------------------------------------------------------------------*/}
        {/* Card-Group*/}
        {/* --------------------------------------------------------------------------------*/}
        <Row>
            <h5 className="mb-3 mt-3">Card Group</h5>
            <Col>
                <CardGroup>
                    <Card>
                        <Card.Img
                            alt="Card image cap"
                            src={bg1}
                            top
                            width="100%" />
                        <Card.Body>
                            <Card.Title as="h5">Card title</Card.Title>
                            <Card.Subtitle
                                className="mb-2 text-muted"
                                as="h6">
                  Card subtitle
                            </Card.Subtitle>
                            <Card.Text>
                  This is a wider card with supporting text below as a natural
                  lead-in to additional content. This content is a little bit
                  longer.
                            </Card.Text>
                            <Button>Button</Button>
                        </Card.Body>
                    </Card>
                    <Card>
                        <Card.Img
                            alt="Card image cap"
                            src={bg2}
                            top
                            width="100%" />
                        <Card.Body>
                            <Card.Title as="h5">Card title</Card.Title>
                            <Card.Subtitle
                                className="mb-2 text-muted"
                                as="h6">
                  Card subtitle
                            </Card.Subtitle>
                            <Card.Text>
                  This card has supporting text below as a natural lead-in to
                  additional content.
                            </Card.Text>
                            <Button>Button</Button>
                        </Card.Body>
                    </Card>
                    <Card>
                        <Card.Img
                            alt="Card image cap"
                            src={bg3}
                            top
                            width="100%" />
                        <Card.Body>
                            <Card.Title as="h5">Card title</Card.Title>
                            <Card.Subtitle
                                className="mb-2 text-muted"
                                as="h6">
                  Card subtitle
                            </Card.Subtitle>
                            <Card.Text>
                  This is a wider card with supporting text below as a natural
                  lead-in to additional content. This card has even longer
                  content than the first to show that equal height action.
                            </Card.Text>
                            <Button>Button</Button>
                        </Card.Body>
                    </Card>
                </CardGroup>
            </Col>
        </Row>
    </div>
)

export default Cards
