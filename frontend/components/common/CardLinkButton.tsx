'use client'

import { useCopyToClipboard } from '@/hooks/useCopyToClipboard'
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
    const { copied, copy } = useCopyToClipboard()

    const handleCopy = () => void copy(`${window.location.origin}/card/${entity}/${id}`)

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
