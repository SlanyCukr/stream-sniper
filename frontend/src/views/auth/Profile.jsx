import React from 'react'
import { Container, Row, Col } from 'react-bootstrap'
import UserProfile from '../../components/auth/UserProfile'

const Profile = () => {
    return (
        <Container className="mt-4">
            <Row>
                <Col lg={8} className="mx-auto">
                    <UserProfile />
                </Col>
            </Row>
        </Container>
    )
}

export default Profile