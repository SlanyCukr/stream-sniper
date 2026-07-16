import { act, fireEvent, render, screen } from '@testing-library/react'
import { forwardRef, useImperativeHandle } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const scrollToIndex = vi.hoisted(() => vi.fn())

vi.mock('react-virtuoso', () => ({
  Virtuoso: forwardRef(function VirtuosoStub({ data, itemContent, endReached }: {
    data: Array<Record<string, unknown>>
    itemContent: CallableFunction
    endReached: CallableFunction
  }, ref) {
    useImperativeHandle(ref, () => ({ scrollToIndex }))
    return (
      <div>
        {data.map((item, index) => <div key={String(item.id)}>{itemContent(index, item)}</div>)}
        <button type="button" onClick={() => endReached()}>reach end</button>
      </div>
    )
  }),
}))

import StreamChatReplay from '@/components/stream/replay/StreamChatReplay'

const messages = [
  { id: 1, ts: '2026-07-14T10:00:00Z', nick: 'one', text: 'first', badges: '' },
  { id: 2, ts: '2026-07-14T10:05:00Z', nick: 'two', text: 'second', badges: '' },
]

describe('StreamChatReplay virtualization boundary', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    scrollToIndex.mockClear()
  })

  afterEach(() => vi.useRealTimers())

  it('scrolls once per nonce and clears the target flash', () => {
    const props = {
      messages,
      hasMore: true,
      isFetchingMore: false,
      onLoadMore: vi.fn(),
      jumpToTs: { ts: '2026-07-14T10:04:00Z', nonce: 4 },
    }
    const { rerender } = render(<StreamChatReplay {...props} />)

    expect(scrollToIndex).toHaveBeenCalledWith({ index: 1, align: 'start' })
    expect(screen.getByText('second').closest('[role="listitem"]')).toHaveClass('chat-line--flash')

    rerender(<StreamChatReplay {...props} messages={[...messages]} />)
    expect(scrollToIndex).toHaveBeenCalledOnce()

    act(() => vi.advanceTimersByTime(1600))
    expect(screen.getByText('second').closest('[role="listitem"]')).not.toHaveClass('chat-line--flash')
  })

  it('requests another page only when pagination is available and idle', () => {
    const onLoadMore = vi.fn()
    const { rerender } = render(
      <StreamChatReplay messages={messages} hasMore={false} isFetchingMore={false} onLoadMore={onLoadMore} jumpToTs={null} />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'reach end' }))
    expect(onLoadMore).not.toHaveBeenCalled()

    rerender(
      <StreamChatReplay messages={messages} hasMore isFetchingMore onLoadMore={onLoadMore} jumpToTs={null} />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'reach end' }))
    expect(onLoadMore).not.toHaveBeenCalled()

    rerender(
      <StreamChatReplay messages={messages} hasMore isFetchingMore={false} onLoadMore={onLoadMore} jumpToTs={null} />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'reach end' }))
    expect(onLoadMore).toHaveBeenCalledOnce()
  })
})
