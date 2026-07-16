import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, test, vi } from 'vitest'

import Pagination from '@/components/common/pagination/Pagination'
import {
  clampPageIndex,
  createPage,
  getPageCount,
  getRowOffset,
} from '@/lib/pagination/page'

describe('pagination model', () => {
  test.each([
    [0, 0],
    [1, 1],
    [20, 1],
    [21, 2],
    [40, 2],
    [41, 3],
  ])('maps total %i to %i pages', (total, expected) => {
    expect(getPageCount(total, 20)).toBe(expected)
  })

  it('converts page indexes only at the row-offset boundary', () => {
    expect(getRowOffset(3, 20)).toBe(60)
    expect(createPage(['row'], 41, 2, 20)).toEqual({
      items: ['row'],
      total: 41,
      pageIndex: 2,
      pageSize: 20,
      pageCount: 3,
    })
  })

  it('clamps an index after the last page disappears', () => {
    expect(clampPageIndex(2, 2)).toBe(1)
    expect(clampPageIndex(3, 0)).toBe(0)
  })
})

describe('Pagination', () => {
  it('provides one zero-based, accessible navigation contract', () => {
    const onPageChange = vi.fn()
    render(
      <Pagination
        pageIndex={2}
        pageCount={6}
        onPageChange={onPageChange}
        ariaLabel="Jobs pagination"
      />,
    )

    expect(screen.getByRole('navigation', { name: 'Jobs pagination' })).toBeInTheDocument()
        expect(screen.getByLabelText('Go to page 3')).toHaveAttribute('aria-current', 'page')

    fireEvent.click(screen.getByRole('button', { name: 'Go to next page' }))
    expect(onPageChange).toHaveBeenCalledWith(3)

    fireEvent.click(screen.getByRole('button', { name: 'Go to first page' }))
    expect(onPageChange).toHaveBeenCalledWith(0)
  })

  it('renders nothing for a single page', () => {
    const { container } = render(
      <Pagination pageIndex={0} pageCount={1} onPageChange={vi.fn()} />,
    )
    expect(container).toBeEmptyDOMElement()
  })
})
