import {
    Card,
} from 'react-bootstrap'
import PropTypes from 'prop-types'

const TopCards = props => (
    <Card>
        <Card.Body>
            <div className="d-flex">
                <div className={`circle-box lg-box d-inline-block ${props.bg}`}>
                    <i
                        className={props.icon}
                        aria-hidden="true">
                    </i>
                </div>
                <div className="ms-3">
                    <h3 className="mb-0 font-weight-bold">{props.earning}</h3>
                    <p className="text-muted mb-0">{props.subtitle}</p>
                </div>
            </div>
        </Card.Body>
    </Card>
)

TopCards.propTypes = {
    bg: PropTypes.string.isRequired,
    icon: PropTypes.string.isRequired,
    earning: PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
    ]).isRequired,
    subtitle: PropTypes.string.isRequired,
}

export default TopCards
