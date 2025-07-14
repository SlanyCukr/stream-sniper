import React, { useState } from 'react'
import {
    Alert,
    Card,
} from 'react-bootstrap'

const Alerts = () => {
    // For Dismiss Button with Alert
    const [
        visible,
        setVisible,
    ] = useState(true)

    const onDismiss = () => {
        setVisible(false)
    }

    return (
        <div>
            {/* --------------------------------------------------------------------------------*/}
            {/* Card-1*/}
            {/* --------------------------------------------------------------------------------*/}
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-bell me-2"> </i>
          Alert
                </Card.Title>
                <Card.Body className="">
                    <div className="mt-3">
                        <Alert variant="primary">
              This is a primary alert— check it out!
                        </Alert>
                        <Alert variant="secondary">
              This is a secondary alert— check it out!
                        </Alert>
                        <Alert variant="success">
              This is a success alert— check it out!
                        </Alert>
                        <Alert variant="danger">This is a danger alert— check it out!</Alert>
                        <Alert variant="warning">
              This is a warning alert— check it out!
                        </Alert>
                        <Alert variant="info">This is a info alert— check it out!</Alert>
                        <Alert variant="light">This is a light alert— check it out!</Alert>
                        <Alert variant="dark">This is a dark alert</Alert>
                    </div>
                </Card.Body>
            </Card>
            {/* --------------------------------------------------------------------------------*/}
            {/* Card-2*/}
            {/* --------------------------------------------------------------------------------*/}
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-bell me-2" />
          Alert with Links
                </Card.Title>
                <Card.Body className="">
                    <div>
                        <Alert variant="primary">
              This is a primary alert with
                            <a
                                href="/"
                                className="alert-link">
                an example link
                            </a>
              . Give it a click if you like.
                        </Alert>
                        <Alert variant="secondary">
              This is a secondary alert with
                            <a
                                href="/"
                                className="alert-link">
                an example link
                            </a>
              . Give it a click if you like.
                        </Alert>
                        <Alert variant="success">
              This is a success alert with
                            <a
                                href="/"
                                className="alert-link">
                an example link
                            </a>
              . Give it a click if you like.
                        </Alert>
                        <Alert variant="danger">
              This is a danger alert with
                            <a
                                href="/"
                                className="alert-link">
                an example link
                            </a>
              . Give it a click if you like.
                        </Alert>
                        <Alert variant="warning">
              This is a warning alert with
                            <a
                                href="/"
                                className="alert-link">
                an example link
                            </a>
              . Give it a click if you like.
                        </Alert>
                        <Alert variant="info">
              This is a info alert with
                            <a
                                href="/"
                                className="alert-link">
                an example link
                            </a>
              . Give it a click if you like.
                        </Alert>
                        <Alert variant="light">
              This is a light alert with
                            <a
                                href="/"
                                className="alert-link">
                an example link
                            </a>
              . Give it a click if you like.
                        </Alert>
                        <Alert variant="dark">
              This is a dark alert with
                            <a
                                href="/"
                                className="alert-link">
                an example link
                            </a>
              . Give it a click if you like.
                        </Alert>
                    </div>
                </Card.Body>
            </Card>
            {/* --------------------------------------------------------------------------------*/}
            {/* Card-3*/}
            {/* --------------------------------------------------------------------------------*/}
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-bell me-2" />
          Alert with Additional content
                </Card.Title>
                <Card.Body className="">
                    <div>
                        <Alert variant="success">
                            <h4 className="alert-heading">Well done!</h4>
                            <p>
                Aww yeah, you successfully read this important alert message.
                This example text is going to run a bit longer so that you can
                see how spacing within an alert works with this kind of content.
                            </p>
                            <hr />
                            <p className="mb-0">
                Whenever you need to, be sure to use margin utilities to keep
                things nice and tidy.
                            </p>
                        </Alert>
                    </div>
                </Card.Body>
            </Card>
            {/* --------------------------------------------------------------------------------*/}
            {/* Card-4*/}
            {/* --------------------------------------------------------------------------------*/}
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-bell me-2" />
          Alert with Dissmissing
                </Card.Title>
                <Card.Body className="">
                    <div>
                        <Alert
                            variant="info"
                            isOpen={visible}
                            toggle={onDismiss.bind(null)}>
              I am an alert and I can be dismissed!
                        </Alert>
                    </div>
                </Card.Body>
            </Card>
            {/* --------------------------------------------------------------------------------*/}
            {/* Card-5*/}
            {/* --------------------------------------------------------------------------------*/}
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-bell me-2" />
          Alert with Uncontrolled [disable] Alerts
                </Card.Title>
                <Card.Body className="">
                    <div>
                        <Alert
                            variant="info"
                            dismissible
                        >
              I am an alert and I can be dismissed!
                        </Alert>
                    </div>
                </Card.Body>
            </Card>
            {/* --------------------------------------------------------------------------------*/}
            {/* Card-6*/}
            {/* --------------------------------------------------------------------------------*/}
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-bell me-2" />
          Alerts without fade
                </Card.Title>
                <Card.Body className="">
                    <div>
                        <Alert
                            variant="primary"
                            isOpen={visible}
                            toggle={onDismiss.bind(null)}
                            fade={false}
                        >
              I am a primary alert and I can be dismissed without animating!
                        </Alert>
                        <Alert
                            variant="warning"
                            dismissible
                            fade={false}>
              I am an alert and I can be dismissed without animating!
                        </Alert>
                    </div>
                </Card.Body>
            </Card>

            {/* --------------------------------------------------------------------------------*/}
            {/* End Inner Div*/}
            {/* --------------------------------------------------------------------------------*/}
        </div>
    )
}

export default Alerts
