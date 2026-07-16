import { fireEvent, render, screen } from '@testing-library/react'
import type { ImgHTMLAttributes } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

/* eslint-disable @next/next/no-img-element, jsx-a11y/alt-text */
vi.mock('next/image', () => ({
  default: (props: ImgHTMLAttributes<HTMLImageElement>) => <img {...props} />,
}))

import StreamThumbnail from '@/components/stream/list/StreamThumbnail'
import ThumbImage from '@/components/stream/list/ThumbImage'
import { router } from './mocks/navigation'

describe('stream cards', () => {
  beforeEach(() => vi.clearAllMocks())

  it('exposes one accessible live-card action for click and keyboard navigation', () => {
    render(
      <StreamThumbnail
        id={42}
        name="Operator"
        start="2026-07-14T10:00:00Z"
        end={null}
        thumbnailSrc={null}
        messageCount={1234}
      />,
    )

    const card = screen.getByRole('button', {
      name: "View details for Operator's stream with 1234 messages",
    })
    expect(screen.getByText('LIVE')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Stream thumbnail for Operator' })).toHaveTextContent('No feed')
    fireEvent.click(card)
    fireEvent.keyDown(card, { key: 'Enter' })
    fireEvent.keyDown(card, { key: ' ' })
    expect(router.push).toHaveBeenCalledTimes(3)
    expect(router.push).toHaveBeenLastCalledWith('/stream/42')
  })

  it('shows ended duration and expands the Twitch thumbnail URL', () => {
    render(
      <StreamThumbnail
        id={43}
        name="Ended"
        start="2026-07-14T10:00:00Z"
        end="2026-07-14T11:30:00Z"
        thumbnailSrc="https://img.test/%{width}x%{height}.jpg"
        messageCount={9}
      />,
    )

    expect(screen.queryByText('LIVE')).not.toBeInTheDocument()
    expect(screen.getByText('1h 30m')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Stream thumbnail for Ended' }))
      .toHaveAttribute('src', 'https://img.test/300x170.jpg')
  })

  it('switches a failed image to the named fallback', () => {
    render(<ThumbImage src="https://img.test/broken.jpg" alt="Broken stream" />)
    fireEvent.error(screen.getByRole('img', { name: 'Broken stream' }))
    expect(screen.getByRole('img', { name: 'Broken stream' })).toHaveTextContent('No feed')
  })
})
