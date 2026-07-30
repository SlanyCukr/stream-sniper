import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { useAuth } = vi.hoisted(() => ({ useAuth: vi.fn() }))

vi.mock('@/contexts/AuthContext', () => ({ useAuth }))

import {
  getDownloadFailure,
  useStreamDownloads,
} from '@/hooks/stream/useStreamDownloads'
import StreamDownloadMenu from '@/components/stream/StreamDownloadMenu'

function DownloadItemsProbe() {
  const { items } = useStreamDownloads(42)
  return <output>{items.map(item => item.label).join('|')}</output>
}

describe('stream download authorization', () => {
  beforeEach(() => vi.clearAllMocks())

  it('uses canonical authentication state for protected chat exports', () => {
    useAuth.mockReturnValue({
      token: 'present-but-expired',
      isAuthenticated: false,
    })
    const { rerender } = render(<DownloadItemsProbe />)

    expect(screen.getByText(/Emotes CSV/)).toBeInTheDocument()
    expect(screen.queryByText(/Chat log \(NDJSON\)/)).not.toBeInTheDocument()

    useAuth.mockReturnValue({
      token: 'valid',
      isAuthenticated: true,
    })
    rerender(<DownloadItemsProbe />)

    expect(screen.getByText(/Chat log \(NDJSON\)/)).toBeInTheDocument()
  })

  it('parses blob error details without mutating the transport error', async () => {
    const body = new Blob([JSON.stringify({ detail: 'export unavailable' })], {
      type: 'application/json',
    })
    const error = {
      message: 'Request failed',
      response: { status: 503, data: body },
    }

    await expect(getDownloadFailure(error)).resolves.toMatchObject({
      error,
      normalized: { message: 'export unavailable', status: 503 },
    })
    expect(error.response.data).toBe(body)
  })

  it('keeps export controls accessible when the stream title is unknown', () => {
    useAuth.mockReturnValue({ token: null, isAuthenticated: false })
    render(<StreamDownloadMenu streamId={42} title={null} />)
    expect(screen.getByRole('button', { name: 'Export stream data' })).toBeInTheDocument()
  })
})
