import React from 'react'
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
