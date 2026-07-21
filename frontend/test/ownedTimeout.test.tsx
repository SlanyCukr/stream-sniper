import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useOwnedTimeout } from '@/hooks/useOwnedTimeout'

describe('useOwnedTimeout', () => {
  afterEach(() => vi.useRealTimers())

  it('replaces earlier work and clears pending work on unmount', () => {
    vi.useFakeTimers()
    const first = vi.fn()
    const replacement = vi.fn()
    const hook = renderHook(() => useOwnedTimeout())

    act(() => {
      hook.result.current.schedule(first, 100)
      hook.result.current.schedule(replacement, 100)
      vi.advanceTimersByTime(100)
    })
    expect(first).not.toHaveBeenCalled()
    expect(replacement).toHaveBeenCalledOnce()

    act(() => hook.result.current.schedule(first, 100))
    hook.unmount()
    act(() => vi.runAllTimers())
    expect(first).not.toHaveBeenCalled()
  })
})
