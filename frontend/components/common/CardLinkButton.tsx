'use client'

import { useState } from 'react'
import { Button } from 'react-bootstrap'

interface CardLinkButtonProps {
    entity: 'stream' | 'creator' | 'chatter'
    id: number | string
}

/**
 * Copies this entity's embeddable-card URL (`/card/{entity}/{id}` — a stable
 * PNG rendered by the card route handlers) so it can be pasted straight into
 * Discord or docs. Uses the live origin so dev/prod links stay correct.
 */
const CardLinkButton = ({ entity, id }: CardLinkButtonProps) => {
    const [copied, setCopied] = useState(false)

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(`${window.location.origin}/card/${entity}/${id}`)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            // Clipboard access denied (permissions/insecure context) — leave
            // the label unchanged rather than pretending it copied.
        }
    }

    return (
        <Button
            variant="outline-secondary"
            size="sm"
            onClick={handleCopy}
            aria-label="Copy shareable card image link">
            <i className="bi bi-card-image me-1" aria-hidden="true"></i>
            {copied ? 'Copied!' : 'Card link'}
        </Button>
    )
}

export default CardLinkButton
