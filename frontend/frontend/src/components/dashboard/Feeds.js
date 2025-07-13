import React from 'react'
import {
    Card,
    ListGroup,
    Button,
} from 'react-bootstrap'

const FeedData = [
    {
        title: 'Cras justo odio',
        icon: 'bi bi-bell',
        color: 'primary',
        date: '6 minute ago',
    },
    {
        title: 'New user registered.',
        icon: 'bi bi-person',
        color: 'info',
        date: '6 minute ago',
    },
    {
        title: 'Server #1 overloaded.',
        icon: 'bi bi-hdd',
        color: 'danger',
        date: '6 minute ago',
    },
    {
        title: 'New order received.',
        icon: 'bi bi-bag-check',
        color: 'success',
        date: '6 minute ago',
    },
    {
        title: 'Cras justo odio',
        icon: 'bi bi-bell',
        color: 'dark',
        date: '6 minute ago',
    },
    {
        title: 'Server #1 overloaded.',
        icon: 'bi bi-hdd',
        color: 'warning',
        date: '6 minute ago',
    },
]

const Feeds = () => (
    <Card>
        <Card.Body>
            <Card.Title as="h3">Feeds</Card.Title>
            <Card.Subtitle
                className="mb-2 text-muted"
                as="p">
          Widget you can use
            </Card.Subtitle>
            <ListGroup
                flush
                className="mt-4"
                role="list"
                aria-label="Activity feed notifications">
                {FeedData.map((feed, index) => (
                    <ListGroup.Item
                        key={index}
                        action
                        href="/"
                        tag="a"
                        className="d-flex align-items-center p-3 border-0"
                        role="listitem"
                        aria-label={`${feed.title}, ${feed.date}`}
                    >
                        <Button
                            className="rounded-circle me-3"
                            size="sm"
                            variant={feed.color}
                            aria-hidden="true"
                        >
                            <i
                                className={feed.icon}
                                aria-hidden="true">
                            </i>
                        </Button>
                        <span>{feed.title}</span>
                        <small className="ms-auto text-muted text-small">
                            {feed.date}
                        </small>
                    </ListGroup.Item>
                ))}
            </ListGroup>
        </Card.Body>
    </Card>
)

export default Feeds
