'use client'

/**
 * Shared markup for the `.status-chip` pill (signal dot + uppercase label)
 * used across admin, moments, chatter, and scene surfaces. This component
 * owns ONLY chip rendering — the class-assembly and modifier vocabulary
 * (`.is-ok` / `.is-warn` / `.is-err`, see `styles/_theme.scss`). Deciding
 * *which* variant a given domain status maps to (job status, active/inactive,
 * health, moment review state, ...) stays a per-call-site concern: keep a
 * small local mapping fn or inline ternary at the call site that returns a
 * `StatusChipVariant` and hand it to this component.
 *
 * @typedef {'ok'|'warn'|'err'|'neutral'} StatusChipVariant
 *
 * @typedef {object} StatusChipProps
 * @property {StatusChipVariant} [variant] Selects the modifier class; 'neutral'
 *   (default) renders the bare `.status-chip` with no `.is-*` modifier.
 * @property {React.ReactNode} [children] Chip label/content.
 * @property {string} [className] Extra classes appended after the variant
 *   modifier (e.g. spacing utilities like `me-2`, or a one-off visual
 *   modifier like `live-chip` that isn't part of the shared ok/warn/err
 *   vocabulary).
 */

const VARIANT_MODIFIERS = {
    ok: ' is-ok',
    warn: ' is-warn',
    err: ' is-err',
    neutral: '',
}

/** @param {StatusChipProps} props */
const StatusChip = ({
    variant = 'neutral',
    children,
    className = '',
    ...rest
}) => {
    const modifier = VARIANT_MODIFIERS[/** @type {StatusChipVariant} */ (variant)] ?? ''
    const classes = `status-chip${modifier}${className ? ` ${className}` : ''}`
    return (
        <span className={classes} {...rest}>
            {children}
        </span>
    )
}

export default StatusChip
