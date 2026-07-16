import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ErrorAlert from '@/components/common/error/ErrorAlert'

describe('ErrorAlert', () => {
  it('owns status, retry, and technical-details behavior', () => {
    const onRetry = vi.fn()
    const error = Object.assign(new Error('request failed'), {
      response: {
        status: 503,
        data: { detail: 'service unavailable' },
        config: { url: '/api/streams', method: 'get' },
      },
    })
    render(
      <ErrorAlert
        error={error}
        title="Streams unavailable"
        onRetry={onRetry}
        showDetails
      />,
    )

    expect(screen.getByText('Streams unavailable')).toBeInTheDocument()
    expect(screen.getByText('503')).toBeInTheDocument()
    expect(screen.getByText('service unavailable')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Retry the failed operation' }))
    expect(onRetry).toHaveBeenCalledOnce()

    fireEvent.click(screen.getByRole('button', { name: 'Show error details' }))
    expect(screen.getByText('Technical Details')).toBeInTheDocument()
    expect(screen.getByText('/api/streams')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Hide error details' }))
    expect(screen.queryByText('Technical Details')).not.toBeInTheDocument()
  })
})
