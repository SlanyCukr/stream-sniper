import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useOverlapModel } from '@/hooks/community/useOverlapModel'

describe('useOverlapModel', () => {
  it('projects names and metrics once while normalizing pair identity', () => {
    const onSelectPair = vi.fn()
    const { result } = renderHook(() => useOverlapModel({
      creators: [
        { creatorId: 1, nick: 'alpha', displayName: 'Alpha' },
        { creatorId: 2, nick: 'beta', displayName: '' },
      ],
      pairs: [{
        a: 2,
        b: 1,
        sharedChatters: 25,
        sharedRegulars: 8,
        jaccardChatters: 0.2,
        jaccardRegulars: 0.1,
      }],
      metric: 'regulars',
      selectedPair: { aId: 2, bId: 1 },
      onSelectPair,
    }))

    expect(result.current.table.rows[0]).toMatchObject({
      aId: 1,
      bId: 2,
      aName: 'Alpha',
      bName: 'beta',
      shared: 8,
      jaccard: 0.1,
    })
    expect(result.current.detail).toMatchObject({ aName: 'Alpha', bName: 'beta' })
    expect(result.current.matrix.cellFor(2, 1)).toMatchObject({ shared: 8, jaccard: 0.1 })
    expect(result.current.matrix.isSelected(1, 2)).toBe(true)

    act(() => result.current.matrix.onSelectPair(2, 1))
    expect(onSelectPair).toHaveBeenCalledWith({ aId: 1, bId: 2 })
  })
})
