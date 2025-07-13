import {
    Card,
    Button,
} from 'react-bootstrap'
import PropTypes from 'prop-types'

const Blog = props => (
    <Card>
        <Card.Img
            alt={`Header image for ${props.title}`}
            src={props.image} />
        <Card.Body className="p-4">
            <Card.Title as="h3">{props.title}</Card.Title>
            <Card.Subtitle
                as="p"
                className="text-muted">
                {props.subtitle}
            </Card.Subtitle>
            <Card.Text className="mt-3">{props.text}</Card.Text>
            <Button
                variant={props.color}
                aria-label={`Read more about ${props.title}`}
            >
                Read More
            </Button>
        </Card.Body>
    </Card>
)

Blog.propTypes = {
    image: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    subtitle: PropTypes.string.isRequired,
    text: PropTypes.string.isRequired,
    color: PropTypes.string.isRequired,
}

export default Blog
