'use client'
import React from 'react'
import Select from 'react-select'
import {
    Card, Container, Row, Col,
} from 'react-bootstrap'
import { AVAILABLE_ORDERING } from '@/constants'

/**
 * Renders filters component
 * @param {Array} creators
 * @param {object} selectedCreator
 * @param {function} onCreatorChange
 * @param {object} selectedOrdering
 * @param {function} onOrderingChange
 * @returns {JSX.Element}
 */
const FiltersCard = React.memo(({
    creators,
    selectedCreator,
    onCreatorChange,
    selectedOrdering,
    onOrderingChange,
}) => (
    <Card>
        <Card.Header>
            <h2 id="filters-heading">Filters</h2>
        </Card.Header>
        <Card.Body>
            <Container>
                <Row>
                    <Col>
                        <label
                            htmlFor="creator-select"
                            className="visually-hidden"
                        >
                            Filter by creator
                        </label>
                        <Select
                            inputId="creator-select"
                            options={creators}
                            value={selectedCreator}
                            onChange={onCreatorChange}
                            placeholder="Select creator..."
                            isClearable
                            aria-label="Filter streams by creator"
                            aria-describedby="creator-help"
                        />
                        <div
                            id="creator-help"
                            className="visually-hidden"
                        >
                            Choose a specific creator to filter streams, or leave empty to show all streams
                        </div>
                    </Col>
                    <Col>
                        <label
                            htmlFor="ordering-select"
                            className="visually-hidden"
                        >
                            Sort streams by
                        </label>
                        <Select
                            inputId="ordering-select"
                            options={AVAILABLE_ORDERING}
                            value={selectedOrdering}
                            onChange={onOrderingChange}
                            placeholder="Sort by..."
                            aria-label="Sort streams by different criteria"
                            aria-describedby="ordering-help"
                        />
                        <div
                            id="ordering-help"
                            className="visually-hidden"
                        >
                            Choose how to sort the streams list
                        </div>
                    </Col>
                </Row>
            </Container>
        </Card.Body>
    </Card>
))

FiltersCard.displayName = 'FiltersCard'

export default FiltersCard
