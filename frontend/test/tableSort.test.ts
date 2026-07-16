import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useTableSort } from '@/hooks/useTableSort'

const getDefaultDirection = (key: string) => (
  key === 'name' ? 'asc' : 'desc'
)

describe('useTableSort', () => {
  it('uses each new column default and toggles the active column', () => {
    const { result } = renderHook(() => useTableSort<string>({
      initialKey: 'rank',
      initialDirection: 'asc',
      getDefaultDirection,
    }))

    act(() => result.current.onSort('messages'))
    expect(result.current).toMatchObject({ sort: 'messages', dir: 'desc' })

    act(() => result.current.onSort('messages'))
    expect(result.current).toMatchObject({ sort: 'messages', dir: 'asc' })

    act(() => result.current.onSort('name'))
    expect(result.current).toMatchObject({ sort: 'name', dir: 'asc' })
  })
})
