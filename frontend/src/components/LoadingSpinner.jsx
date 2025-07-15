import React from 'react'
import {
    Spinner, Card,
} from 'react-bootstrap'
import PropTypes from 'prop-types'

/**
 * Size configuration for spinners
 */
const SIZE_MAP = {
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

/**
 * Creates spinner props based on configuration
 */
const createSpinnerProps = (size, variant, text, props) => ({
    animation: 'border',
    variant,
    style: SIZE_MAP[size],
    role: 'status',
    'aria-label': text,
    ...props,
})

/**
 * Renders the basic spinner content with optional text
 */
const SpinnerContent = ({
    spinnerProps, text, centered, className,
}) => (
    <div className={`d-flex align-items-center ${centered ? 'justify-content-center' : ''} ${className}`}>
        <Spinner {...spinnerProps}>
            <span className="visually-hidden">{text}</span>
        </Spinner>
        {text && (
            <span
                className="ms-2"
                aria-live="polite">
                {text}
            </span>
        )}
    </div>
)

/**
 * Renders spinner with overlay style
 */
const OverlaySpinner = ({ children }) => (
    <div
        className="position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center bg-white bg-opacity-75"
        style={{ zIndex: 1000 }}
    >
        {children}
    </div>
)

/**
 * Renders spinner inside a card
 */
const CardSpinner = ({ children }) => (
    <Card className="text-center">
        <Card.Body className="py-5">
            {children}
        </Card.Body>
    </Card>
)

/**
 * Renders centered spinner wrapper
 */
const CenteredSpinner = ({ children }) => (
    <div className="text-center py-4">
        {children}
    </div>
)

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
    const spinnerProps = createSpinnerProps(size, variant, text, props)

    const content = (
        <SpinnerContent
            spinnerProps={spinnerProps}
            text={text}
            centered={centered}
            className={className}
        />
    )

    if (overlay) {
        return <OverlaySpinner>{content}</OverlaySpinner>
    }

    if (card) {
        return <CardSpinner>{content}</CardSpinner>
    }

    return centered ? <CenteredSpinner>{content}</CenteredSpinner> : content
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
