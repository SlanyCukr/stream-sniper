import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import QueryState from '@/components/common/QueryState'

const content = (data: unknown) => <div data-testid="content">{JSON.stringify(data)}</div>

describe('QueryState', () => {
    it('renders the loading spinner while pending with no data', () => {
        render(
            <QueryState query={{ isLoading: true }} loadingText="Loading community…">
                {content}
            </QueryState>,
        )

        expect(screen.getByRole('status')).toBeTruthy()
        expect(screen.queryByTestId('content')).toBeNull()
    })

    it('renders the error alert with a retry wired to refetch when there is no data', () => {
        const refetch = vi.fn()
        const error = Object.assign(new Error('request failed'), {
            response: { status: 503, data: { detail: 'service unavailable' } },
        })

        render(
            <QueryState query={{ error, refetch }} errorTitle="Failed to load community">
                {content}
            </QueryState>,
        )

        expect(screen.getByText('Failed to load community')).toBeTruthy()
        fireEvent.click(screen.getByRole('button', { name: /retry/i }))
        expect(refetch).toHaveBeenCalledTimes(1)
        expect(screen.queryByTestId('content')).toBeNull()
    })

    it('keeps rendering stale data when a refetch error arrives (data wins over transient error)', () => {
        const error = new Error('background refetch failed')

        render(
            <QueryState query={{ data: [1, 2, 3], error }}>
                {content}
            </QueryState>,
        )

        expect(screen.getByTestId('content').textContent).toBe('[1,2,3]')
    })

    it('renders the empty slot when the empty predicate matches resolved data', () => {
        render(
            <QueryState
                query={{ data: [] }}
                isEmpty={(rows: unknown[]) => rows.length === 0}
                emptyTitle="No overlap computed yet"
                emptyHint="Run the rollup backfill."
            >
                {content}
            </QueryState>,
        )

        expect(screen.getByText('No overlap computed yet')).toBeTruthy()
        expect(screen.queryByTestId('content')).toBeNull()
    })

    it('prefers a custom emptyState node over the title/hint shorthand', () => {
        render(
            <QueryState
                query={{ data: [] }}
                isEmpty={(rows: unknown[]) => rows.length === 0}
                emptyState={<div data-testid="custom-empty">custom</div>}
                emptyTitle="ignored"
            >
                {content}
            </QueryState>,
        )

        expect(screen.getByTestId('custom-empty')).toBeTruthy()
        expect(screen.queryByText('ignored')).toBeNull()
    })

    it('passes resolved data to the render prop', () => {
        render(
            <QueryState query={{ data: { name: 'loop' } }}>
                {content}
            </QueryState>,
        )

        expect(screen.getByTestId('content').textContent).toBe('{"name":"loop"}')
    })

    it('treats an idle query with no data, error, or loading as empty', () => {
        render(
            <QueryState query={{}} emptyTitle="Nothing selected">
                {content}
            </QueryState>,
        )

        expect(screen.getByText('Nothing selected')).toBeTruthy()
        expect(screen.queryByTestId('content')).toBeNull()
    })
})
