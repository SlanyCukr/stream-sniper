'use client'
import {
    Card, Col, Row,
} from 'react-bootstrap'
import CreateUserForm from '@/components/admin/users/CreateUserForm'

const CreateUser = () => (
    <>
        <div className="page-head">
            <div>
                <h1 className="page-title">Create user</h1>
                <p className="page-sub">Provision a new account</p>
            </div>
        </div>
        <Row>
            <Col lg={8} className="mx-auto">
                <Card>
                    <Card.Body>
                        <h3 className="section-label mb-3">Account details</h3>
                        <CreateUserForm />
                    </Card.Body>
                </Card>
            </Col>
        </Row>
    </>
)

export default CreateUser
