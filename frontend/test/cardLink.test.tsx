import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CardLinkButton from '@/components/common/CardLinkButton'

describe('CardLinkButton', () => {
  afterEach(() => vi.unstubAllGlobals())

  const stubClipboard = () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    return writeText
  }

  it('copies the absolute embeddable-card URL for the entity', async () => {
    const writeText = stubClipboard()
    render(<CardLinkButton entity="stream" id={77} />)

    fireEvent.click(screen.getByRole('button', { name: 'Copy shareable card image link' }))

    await waitFor(() => expect(writeText).toHaveBeenCalledWith(
      `${window.location.origin}/card/stream/77`,
    ))
    expect(await screen.findByText('Copied!')).toBeInTheDocument()
  })

  it('keeps the idle label when clipboard access is denied', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'))
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    render(<CardLinkButton entity="chatter" id={5} />)

    fireEvent.click(screen.getByRole('button', { name: 'Copy shareable card image link' }))

    await waitFor(() => expect(writeText).toHaveBeenCalled())
    expect(screen.getByText('Card link')).toBeInTheDocument()
    expect(screen.queryByText('Copied!')).not.toBeInTheDocument()
  })
})
