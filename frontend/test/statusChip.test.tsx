import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import StatusChip from '@/components/common/StatusChip'

describe('StatusChip', () => {
    it('renders the bare chip with no modifier when variant is omitted', () => {
        render(<StatusChip>Inactive</StatusChip>)

        const chip = screen.getByText('Inactive')
        expect(chip.className).toBe('status-chip')
    })

    it('renders the bare chip with no modifier for variant="neutral"', () => {
        render(<StatusChip variant="neutral">Idle</StatusChip>)

        expect(screen.getByText('Idle').className).toBe('status-chip')
    })

    it('applies the is-ok modifier for variant="ok"', () => {
        render(<StatusChip variant="ok">Healthy</StatusChip>)

        expect(screen.getByText('Healthy').className).toBe('status-chip is-ok')
    })

    it('applies the is-warn modifier for variant="warn"', () => {
        render(<StatusChip variant="warn">Degraded</StatusChip>)

        expect(screen.getByText('Degraded').className).toBe('status-chip is-warn')
    })

    it('applies the is-err modifier for variant="err"', () => {
        render(<StatusChip variant="err">Unhealthy</StatusChip>)

        expect(screen.getByText('Unhealthy').className).toBe('status-chip is-err')
    })

    it('appends a pass-through className after the variant modifier', () => {
        render(<StatusChip variant="ok" className="live-chip">LIVE</StatusChip>)

        expect(screen.getByText('LIVE').className).toBe('status-chip is-ok live-chip')
    })

    it('appends a pass-through className when no variant is given', () => {
        render(<StatusChip className="me-2">Queued</StatusChip>)

        expect(screen.getByText('Queued').className).toBe('status-chip me-2')
    })

    it('renders children/label content and forwards extra attributes', () => {
        render(
            <StatusChip variant="warn" aria-label="This chatter is flagged as a bot">
                BOT
            </StatusChip>,
        )

        const chip = screen.getByLabelText('This chatter is flagged as a bot')
        expect(chip.tagName).toBe('SPAN')
        expect(chip.textContent).toBe('BOT')
    })
})
