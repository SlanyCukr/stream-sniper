/* eslint-disable react/no-unescaped-entities */
import {
    Card, Row, Col, Button, Form,
} from 'react-bootstrap'

const Forms = () => (
    <Row>
        <Col>
            {/* --------------------------------------------------------------------------------*/}
            {/* Card-1*/}
            {/* --------------------------------------------------------------------------------*/}
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-bell me-2"> </i>
            Form Example
                </Card.Title>
                <Card.Body>
                    <Form>
                        <Form.Group>
                            <Form.Label for="exampleEmail">Email</Form.Label>
                            <Form.Control
                                id="exampleEmail"
                                name="email"
                                placeholder="with a placeholder"
                                type="email"
                            />
                        </Form.Group>
                        <Form.Group>
                            <Form.Label for="examplePassword">Password</Form.Label>
                            <Form.Control
                                id="examplePassword"
                                name="password"
                                placeholder="password placeholder"
                                type="password"
                            />
                        </Form.Group>
                        <Form.Group>
                            <Form.Label for="exampleSelect">Select</Form.Label>
                            <Form.Control
                                id="exampleSelect"
                                name="select"
                                type="select">
                                <option>1</option>
                                <option>2</option>
                                <option>3</option>
                                <option>4</option>
                                <option>5</option>
                            </Form.Control>
                        </Form.Group>
                        <Form.Group>
                            <Form.Label for="exampleSelectMulti">Select Multiple</Form.Label>
                            <Form.Control
                                id="exampleSelectMulti"
                                multiple
                                name="selectMulti"
                                type="select"
                            >
                                <option>1</option>
                                <option>2</option>
                                <option>3</option>
                                <option>4</option>
                                <option>5</option>
                            </Form.Control>
                        </Form.Group>
                        <Form.Group>
                            <Form.Label for="exampleText">Text Area</Form.Label>
                            <Form.Control
                                id="exampleText"
                                name="text"
                                type="textarea" />
                        </Form.Group>
                        <Form.Group>
                            <Form.Label for="exampleFile">File</Form.Label>
                            <Form.Control
                                id="exampleFile"
                                name="file"
                                type="file" />
                            <Form.Text>
                  This is some placeholder block-level help text for the above
                  input. It's a bit lighter and easily wraps to a new line.
                            </Form.Text>
                        </Form.Group>
                        <Form.Group tag="fieldset">
                            <legend>Radio Buttons</legend>
                            <Form.Group check>
                                <Form.Control
                                    name="radio1"
                                    type="radio" />{' '}
                                <Form.Label check>
                    Option one is this and that—be sure to include why it's
                    great
                                </Form.Label>
                            </Form.Group>
                            <Form.Group check>
                                <Form.Control
                                    name="radio1"
                                    type="radio" />{' '}
                                <Form.Label check>
                    Option two can be something else and selecting it will
                    deselect option one
                                </Form.Label>
                            </Form.Group>
                            <Form.Group
                                check
                                disabled>
                                <Form.Control
                                    disabled
                                    name="radio1"
                                    type="radio" />{' '}
                                <Form.Label check>Option three is disabled</Form.Label>
                            </Form.Group>
                        </Form.Group>
                        <Form.Group check>
                            <Form.Control type="checkbox" /> <Form.Label check>Check me out</Form.Label>
                        </Form.Group>
                        <Button>Submit</Button>
                    </Form>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default Forms
