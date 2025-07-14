import ProjectTables from '../../components/dashboard/ProjectTable'
import {
    Row, Col, Table, Card,
} from 'react-bootstrap'

const Tables = () => (
    <Row>
        {/* --------------------------------------------------------------------------------*/}
        {/* table-1*/}
        {/* --------------------------------------------------------------------------------*/}
        <Col lg="12">
            <ProjectTables />
        </Col>
        {/* --------------------------------------------------------------------------------*/}
        {/* table-2*/}
        {/* --------------------------------------------------------------------------------*/}
        <Col lg="12">
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-card-text me-2"> </i>
            Table with Border
                </Card.Title>
                <Card.Body className="">
                    <Table bordered>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>First Name</th>
                                <th>Last Name</th>
                                <th>Username</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th scope="row">1</th>
                                <td>Mark</td>
                                <td>Otto</td>
                                <td>@mdo</td>
                            </tr>
                            <tr>
                                <th scope="row">2</th>
                                <td>Jacob</td>
                                <td>Thornton</td>
                                <td>@fat</td>
                            </tr>
                            <tr>
                                <th scope="row">3</th>
                                <td>Larry</td>
                                <td>the Bird</td>
                                <td>@twitter</td>
                            </tr>
                        </tbody>
                    </Table>
                </Card.Body>
            </Card>
        </Col>
        {/* --------------------------------------------------------------------------------*/}
        {/* table-3*/}
        {/* --------------------------------------------------------------------------------*/}
        <Col lg="12">
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-card-text me-2"> </i>
            Table with Striped
                </Card.Title>
                <Card.Body className="">
                    <Table
                        bordered
                        striped>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>First Name</th>
                                <th>Last Name</th>
                                <th>Username</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th scope="row">1</th>
                                <td>Mark</td>
                                <td>Otto</td>
                                <td>@mdo</td>
                            </tr>
                            <tr>
                                <th scope="row">2</th>
                                <td>Jacob</td>
                                <td>Thornton</td>
                                <td>@fat</td>
                            </tr>
                            <tr>
                                <th scope="row">3</th>
                                <td>Larry</td>
                                <td>the Bird</td>
                                <td>@twitter</td>
                            </tr>
                        </tbody>
                    </Table>
                </Card.Body>
            </Card>
        </Col>
        {/* --------------------------------------------------------------------------------*/}
        {/* table-3*/}
        {/* --------------------------------------------------------------------------------*/}
        <Col lg="12">
            <Card>
                <Card.Title
                    as="h6"
                    className="border-bottom p-3 mb-0">
                    <i className="bi bi-card-text me-2"> </i>
            Table with Hover
                </Card.Title>
                <Card.Body className="">
                    <Table
                        bordered
                        hover>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>First Name</th>
                                <th>Last Name</th>
                                <th>Username</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th scope="row">1</th>
                                <td>Mark</td>
                                <td>Otto</td>
                                <td>@mdo</td>
                            </tr>
                            <tr>
                                <th scope="row">2</th>
                                <td>Jacob</td>
                                <td>Thornton</td>
                                <td>@fat</td>
                            </tr>
                            <tr>
                                <th scope="row">3</th>
                                <td>Larry</td>
                                <td>the Bird</td>
                                <td>@twitter</td>
                            </tr>
                        </tbody>
                    </Table>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default Tables
