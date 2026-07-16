'use client'
import React from 'react'
import {
    Spinner, Card,
} from 'react-bootstrap'

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

/** @typedef {'sm'|'md'|'lg'|'xl'} LoadingSize */
/** @typedef {Omit<React.ComponentProps<typeof Spinner>, 'size'> & {size?:LoadingSize, text?:string, centered?:boolean, overlay?:boolean, card?:boolean, className?:string}} LoadingSpinnerProps */

/**
 * @param {LoadingSize} size
 * @param {string} variant
 * @param {string} text
 * @param {React.ComponentProps<typeof Spinner>} props
 */
const createSpinnerProps = (size, variant, text, props) => ({
    animation: /** @type {'border'} */ ('border'),
    variant,
    style: SIZE_MAP[size],
    role: 'status',
    'aria-label': text,
    ...props,
})

/** @param {{spinnerProps:React.ComponentProps<typeof Spinner>, text:string, centered:boolean, className:string}} props */
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

/** @param {{children:React.ReactNode}} props */
const OverlaySpinner = ({ children }) => (
    <div
        className="position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
        style={{
            zIndex: 1000,
            background: 'rgba(11, 14, 19, 0.75)',
            backdropFilter: 'blur(2px)',
        }}
    >
        {children}
    </div>
)

/** @param {{children:React.ReactNode}} props */
const CardSpinner = ({ children }) => (
    <Card className="text-center">
        <Card.Body className="py-5">
            {children}
        </Card.Body>
    </Card>
)

/** @param {{children:React.ReactNode}} props */
const CenteredSpinner = ({ children }) => (
    <div className="text-center py-4">
        {children}
    </div>
)

/** @param {LoadingSpinnerProps} props */
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

export default React.memo(LoadingSpinner)
