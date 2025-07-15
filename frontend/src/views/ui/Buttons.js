/* eslint-disable max-lines */
import { useState } from 'react'
import {
    Button, ButtonGroup, Card, Row, Col,
} from 'react-bootstrap'

const Buttons = () => {
    const [
        cSelected,
        setCSelected,
    ] = useState([
    ])
    const [
        rSelected,
        setRSelected,
    ] = useState(null)

    // eslint-disable-next-line no-shadow
    const onRadioBtnClick = rSelected => {
        setRSelected(rSelected)
    }

    const onCheckboxBtnClick = selected => {
        const index = cSelected.indexOf(selected)
        if (index < 0) {
            cSelected.push(selected)
        } else {
            cSelected.splice(index, 1)
        }
        setCSelected([
            ...cSelected,
        ])
    }

    return (
        <div>
            {/* --------------------------------------------------------------------------------*/}
            {/* Start Inner Div*/}
            {/* --------------------------------------------------------------------------------*/}
            {/* --------------------------------------------------------------------------------*/}
            {/* Row*/}
            {/* --------------------------------------------------------------------------------*/}
            <Row>
                <Col
                    xs="12"
                    md="6">
                    {/* --------------------------------------------------------------------------------*/}
                    {/* Card-1*/}
                    {/* --------------------------------------------------------------------------------*/}
                    <Card>
                        <Card.Title
                            as="h6"
                            className="border-bottom p-3 mb-0">
              Buttons
                        </Card.Title>
                        <Card.Body className="">
                            <div className="button-group">
                                <Button
                                    className="btn"
                                    variant="primary">
                  primary
                                </Button>
                                <Button
                                    className="btn"
                                    variant="secondary">
                  secondary
                                </Button>
                                <Button
                                    className="btn"
                                    variant="success">
                  success
                                </Button>
                                <Button
                                    className="btn"
                                    variant="info">
                  info
                                </Button>
                                <Button
                                    className="btn"
                                    variant="warning">
                  warning
                                </Button>
                                <Button
                                    className="btn"
                                    variant="danger">
                  danger
                                </Button>
                                <Button
                                    className="btn"
                                    color="link">
                  link
                                </Button>
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
                <Col
                    xs="12"
                    md="6">
                    {/* --------------------------------------------------------------------------------*/}
                    {/* Card-2*/}
                    {/* --------------------------------------------------------------------------------*/}
                    <Card>
                        <Card.Title
                            as="h6"
                            className="border-bottom p-3 mb-0">
              Outline Buttons
                        </Card.Title>
                        <Card.Body className="">
                            <div className="button-group">
                                <Button
                                    className="btn"
                                    outline
                                    variant="primary">
                  primary
                                </Button>
                                <Button
                                    className="btn"
                                    outline
                                    variant="secondary">
                  secondary
                                </Button>
                                <Button
                                    className="btn"
                                    outline
                                    variant="success">
                  success
                                </Button>
                                <Button
                                    className="btn"
                                    outline
                                    variant="info">
                  info
                                </Button>
                                <Button
                                    className="btn"
                                    outline
                                    variant="warning">
                  warning
                                </Button>
                                <Button
                                    className="btn"
                                    outline
                                    variant="danger">
                  danger
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
              Large Size Buttons
                        </Card.Title>
                        <Card.Body className="">
                            <div className="button-group">
                                <Button
                                    className="btn"
                                    variant="primary"
                                    size="lg">
                  Large Button
                                </Button>
                                <Button
                                    className="btn"
                                    variant="secondary"
                                    size="lg">
                  Large Button
                                </Button>
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
              Small Size Buttons
                        </Card.Title>
                        <Card.Body className="">
                            <div className="button-group">
                                <Button
                                    className="btn"
                                    variant="primary"
                                    size="sm">
                  Small Button
                                </Button>
                                <Button
                                    className="btn"
                                    variant="secondary"
                                    size="sm">
                  Small Button
                                </Button>
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
                <Col
                    xs="12"
                    md="6">
                    {/* --------------------------------------------------------------------------------*/}
                    {/* Card-6*/}
                    {/* --------------------------------------------------------------------------------*/}
                    <Card>
                        <Card.Title
                            as="h6"
                            className="border-bottom p-3 mb-0">
              Active State Buttons
                        </Card.Title>
                        <Card.Body className="">
                            <div className="button-group">
                                <Button
                                    className="btn"
                                    variant="primary"
                                    size="lg"
                                    active>
                  Primary link
                                </Button>
                                <Button
                                    className="btn"
                                    variant="secondary"
                                    size="lg"
                                    active>
                  Link
                                </Button>
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
                <Col
                    xs="12"
                    md="6">
                    {/* --------------------------------------------------------------------------------*/}
                    {/* Card-7*/}
                    {/* --------------------------------------------------------------------------------*/}
                    <Card>
                        <Card.Title
                            as="h6"
                            className="border-bottom p-3 mb-0">
              Disabled State Buttons
                        </Card.Title>
                        <Card.Body className="">
                            <div className="button-group">
                                <Button
                                    className="btn"
                                    variant="primary"
                                    size="lg"
                                    disabled>
                  Primary button
                                </Button>
                                <Button
                                    className="btn"
                                    variant="secondary"
                                    size="lg"
                                    disabled>
                  Button
                                </Button>
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
              Block Buttons
                        </Card.Title>
                        <Card.Body className="">
                            <div className="button-group">
                                <Button
                                    className="btn"
                                    variant="primary"
                                    size="lg"
                                    block>
                  Block level button
                                </Button>
                                <Button
                                    className="btn"
                                    variant="secondary"
                                    size="lg"
                                    block>
                  Block level button
                                </Button>
                            </div>
                        </Card.Body>
                    </Card>
                </Col>
                <Col
                    xs="12"
                    md="6">
                    {/* --------------------------------------------------------------------------------*/}
                    {/* Card-6*/}
                    {/* --------------------------------------------------------------------------------*/}
                    <Card>
                        <Card.Title
                            as="h6"
                            className="border-bottom p-3 mb-0">
              Checkbox(Stateful Buttons)
                        </Card.Title>
                        <Card.Body className="">
                            <h5>Checkbox Buttons</h5>
                            <ButtonGroup>
                                <Button
                                    variant="primary"
                                    onClick={() => onCheckboxBtnClick(1)}
                                    active={cSelected.includes(1)}
                                >
                  One
                                </Button>
                                <Button
                                    variant="primary"
                                    onClick={() => onCheckboxBtnClick(2)}
                                    active={cSelected.includes(2)}
                                >
                  Two
                                </Button>
                                <Button
                                    variant="primary"
                                    onClick={() => onCheckboxBtnClick(3)}
                                    active={cSelected.includes(3)}
                                >
                  Three
                                </Button>
                            </ButtonGroup>
                            <p className="mb-0">Selected: {JSON.stringify(cSelected)}</p>
                        </Card.Body>
                    </Card>
                </Col>
                <Col
                    xs="12"
                    md="6">
                    {/* --------------------------------------------------------------------------------*/}
                    {/* Card-6*/}
                    {/* --------------------------------------------------------------------------------*/}
                    <Card>
                        <Card.Title
                            as="h6"
                            className="border-bottom p-3 mb-0">
              Radio Buttons (Stateful Buttons)
                        </Card.Title>
                        <Card.Body className="">
                            <h5>Radio Buttons</h5>
                            <ButtonGroup>
                                <Button
                                    variant="primary"
                                    onClick={() => onRadioBtnClick(1)}
                                    active={rSelected === 1}
                                >
                  One
                                </Button>
                                <Button
                                    variant="primary"
                                    onClick={() => onRadioBtnClick(2)}
                                    active={rSelected === 2}
                                >
                  Two
                                </Button>
                                <Button
                                    variant="primary"
                                    onClick={() => onRadioBtnClick(3)}
                                    active={rSelected === 3}
                                >
                  Three
                                </Button>
                            </ButtonGroup>
                            <p className="mb-0">Selected: {rSelected}</p>
                        </Card.Body>
                    </Card>
                </Col>
            </Row>
            {/* --------------------------------------------------------------------------------*/}
            {/* Row*/}
            {/* --------------------------------------------------------------------------------*/}

            {/* --------------------------------------------------------------------------------*/}
            {/* End Inner Div*/}
            {/* --------------------------------------------------------------------------------*/}
        </div>
    )
}

export default Buttons
