import React from 'react'
import {
    Spinner, Card,
} from 'react-bootstrap'
import PropTypes from 'prop-types'

/**
 * Enhanced loading spinner component with various styles and sizes
 */
const LoadingSpinner = ({
    size = 'md',
    variant = 'primary',
    text = 'Loading...',
    centered = true,
    overlay = false,
    card = false,
    className = '',
    ...props
}) => {
    const sizeMap = {
        sm: {
            width: '1rem',
            height: '1rem',
        },
        md: {
            width: '2rem',
            height: '2rem',
        },
        lg: {
            width: '3rem',
            height: '3rem',
        },
        xl: {
            width: '4rem',
            height: '4rem',
        },
    }

    const spinnerProps = {
        animation: 'border',
        variant,
        style: sizeMap[size],
        role: 'status',
        'aria-label': text,
        ...props,
    }

    const content = (
        <div className={`d-flex align-items-center ${centered ? 'justify-content-center' : ''} ${className}`}>
            <Spinner {...spinnerProps}>
                <span className="visually-hidden">{text}</span>
            </Spinner>
            {text && (
                <span className="ms-2" aria-live="polite">
                    {text}
                </span>
            )}
        </div>
    )

    if (overlay) {
        return (
            <div 
                className="position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center bg-white bg-opacity-75"
                style={{
                    zIndex: 1000,
                }}
            >
                {content}
            </div>
        )
    }

    if (card) {
        return (
            <Card className="text-center">
                <Card.Body className="py-5">
                    {content}
                </Card.Body>
            </Card>
        )
    }

    return centered ? (
        <div className="text-center py-4">
            {content}
        </div>
    ) : content
}

LoadingSpinner.propTypes = {
    size: PropTypes.oneOf([
        'sm',
        'md',
        'lg',
        'xl',
    ]),
    variant: PropTypes.oneOf([
        'primary',
        'secondary',
        'success',
        'danger',
        'warning',
        'info',
        'light',
        'dark',
    ]),
    text: PropTypes.string,
    centered: PropTypes.bool,
    overlay: PropTypes.bool,
    card: PropTypes.bool,
    className: PropTypes.string,
}

export default React.memo(LoadingSpinner)