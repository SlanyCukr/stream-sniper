// React import not needed since React 17+
import './loader.scss'
import {
    Spinner,
} from 'react-bootstrap'

const Loader = () => (
    <div className="fallback-spinner">
        <div className="loading">
            <Spinner
                animation="border"
                variant="primary"
            />
        </div>
    </div>
)
export default Loader
