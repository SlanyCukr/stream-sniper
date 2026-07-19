'use client'

import {
    Container, Row, Col,
} from 'react-bootstrap'
import UserProfile from '@/components/auth/profile/UserProfile'

const Profile = () => (
    <Container className="p-0">
        <div className="page-head">
            <div>
                <h1 className="page-title">Operator profile</h1>
                <p className="page-sub">Account &amp; credentials</p>
            </div>
        </div>
        <Row>
            <Col
                lg={8}
                className="mx-auto">
                <UserProfile />
            </Col>
        </Row>
    </Container>
)

export default Profile
