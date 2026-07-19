'use client'
import type { ReactNode, HTMLAttributes } from 'react'

/**
 * Shared markup for the `.status-chip` pill (signal dot + uppercase label)
 * used across admin, moments, chatter, and scene surfaces. This component
 * owns ONLY chip rendering — the class-assembly and modifier vocabulary
 * (`.is-ok` / `.is-warn` / `.is-err`, see `styles/_theme.scss`). Deciding
 * *which* variant a given domain status maps to (job status, active/inactive,
 * health, moment review state, ...) stays a per-call-site concern: keep a
 * small local mapping fn or inline ternary at the call site that returns a
 * `StatusChipVariant` and hand it to this component.
 */

export type StatusChipVariant = 'ok' | 'warn' | 'err' | 'neutral'

interface StatusChipProps extends HTMLAttributes<HTMLSpanElement> {
    /** Selects the modifier class; 'neutral' (default) renders the bare `.status-chip` with no `.is-*` modifier. */
    variant?: StatusChipVariant
    /** Chip label/content. */
    children?: ReactNode
    /**
     * Extra classes appended after the variant modifier (e.g. spacing utilities
     * like `me-2`, or a one-off visual modifier like `live-chip` that isn't part
     * of the shared ok/warn/err vocabulary).
     */
    className?: string
}

const VARIANT_MODIFIERS: Record<StatusChipVariant, string> = {
    ok: ' is-ok',
    warn: ' is-warn',
    err: ' is-err',
    neutral: '',
}

const StatusChip = ({
    variant = 'neutral',
    children,
    className = '',
    ...rest
}: StatusChipProps) => {
    const modifier = VARIANT_MODIFIERS[variant] ?? ''
    const classes = `status-chip${modifier}${className ? ` ${className}` : ''}`
    return (
        <span className={classes} {...rest}>
            {children}
        </span>
    )
}

export default StatusChip
