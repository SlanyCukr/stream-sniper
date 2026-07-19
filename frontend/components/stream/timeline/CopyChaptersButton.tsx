'use client'
import { useState } from 'react'
import { Button } from 'react-bootstrap'
import { buildVodChapters } from '@/utils/vodChapters'

interface CopyChaptersButtonProps {
    timeline: Parameters<typeof buildVodChapters>[0]
}

/**
 * Copies a chapter list (moment offsets + Twitch VOD deep links) to the
 * clipboard. Renders nothing when the stream has no VOD id or no moments —
 * there would be nothing to copy.
 */
const CopyChaptersButton = ({ timeline }: CopyChaptersButtonProps) => {
    const [copied, setCopied] = useState(false)
    const chapters = buildVodChapters(timeline)

    if (!chapters) return null

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(chapters)
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
            aria-label="Copy VOD chapter list to clipboard">
            <i className="bi bi-list-ol me-1" aria-hidden="true"></i>
            {copied ? 'Copied!' : 'Copy chapters'}
        </Button>
    )
}

export default CopyChaptersButton
