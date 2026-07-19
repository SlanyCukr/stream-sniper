'use client'
import React, { type ComponentProps, type ReactNode } from 'react'
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

export type LoadingSize = 'sm' | 'md' | 'lg' | 'xl'

type SpinnerProps = ComponentProps<typeof Spinner>

export type LoadingSpinnerProps = Omit<SpinnerProps, 'size'> & {
    size?: LoadingSize
    text?: string
    centered?: boolean
    overlay?: boolean
    card?: boolean
    className?: string
}

const createSpinnerProps = (
    size: LoadingSize,
    variant: LoadingSpinnerProps['variant'],
    text: LoadingSpinnerProps['text'],
    props: SpinnerProps,
): SpinnerProps => ({
    animation: 'border',
    variant,
    style: SIZE_MAP[size],
    role: 'status',
    'aria-label': text,
    ...props,
})

interface SpinnerContentProps {
    spinnerProps: SpinnerProps
    text: string | undefined
    centered: boolean
    className: string
}

const SpinnerContent = ({
    spinnerProps, text, centered, className,
}: SpinnerContentProps) => (
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

const OverlaySpinner = ({ children }: { children: ReactNode }) => (
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

const CardSpinner = ({ children }: { children: ReactNode }) => (
    <Card className="text-center">
        <Card.Body className="py-5">
            {children}
        </Card.Body>
    </Card>
)

const CenteredSpinner = ({ children }: { children: ReactNode }) => (
    <div className="text-center py-4">
        {children}
    </div>
)

const LoadingSpinner = ({
    size = 'md',
    variant = 'primary',
    text = 'Loading...',
    centered = true,
    overlay = false,
    card = false,
    className = '',
    ...props
}: LoadingSpinnerProps) => {
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
