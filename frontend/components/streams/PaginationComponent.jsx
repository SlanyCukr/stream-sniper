'use client'
import React from 'react'
import { Pagination } from 'react-bootstrap'

/**
 * Renders pagination component
 * @param {number} pagesCount
 * @param {number} offset
 * @param {function} updateOffset
 * @returns {JSX.Element|null}
 */
const PaginationComponent = React.memo(({
    pagesCount, offset, updateOffset,
}) => {
    if (pagesCount === 0) {
        return null
    }

    // Handle keyboard navigation for pagination
    const handleKeyDown = (event, action) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            action()
        }
    }

    const isFirstPage = offset === 0
    const isLastPage = offset + 1 === pagesCount

    return (
        <nav
            aria-label="Stream pagination navigation"
            className="h-100 d-flex align-items-center justify-content-center p-1"
        >
            <Pagination
                size="lg"
            >
                <Pagination.First
                    onClick={() => updateOffset(0)}
                    onKeyDown={e => handleKeyDown(e, () => updateOffset(0))}
                    disabled={isFirstPage}
                    aria-label="Go to first page"
                    tabIndex={0}
                />
                <Pagination.Prev
                    disabled={isFirstPage}
                    onClick={() => updateOffset(offset - 1)}
                    onKeyDown={e => handleKeyDown(e, () => updateOffset(offset - 1))}
                    aria-label="Go to previous page"
                    tabIndex={0}
                />
                {Array.from({ length: pagesCount }, (_, k) => (
                    <Pagination.Item
                        active={k === offset}
                        key={k + 1}
                        onClick={() => updateOffset(k)}
                        onKeyDown={e => handleKeyDown(e, () => updateOffset(k))}
                        aria-label={`Go to page ${k + 1}`}
                        aria-current={k === offset ? 'page' : null}
                        tabIndex={0}
                    >
                        {k + 1}
                    </Pagination.Item>
                ))}
                <Pagination.Next
                    disabled={isLastPage}
                    onClick={() => updateOffset(offset + 1)}
                    onKeyDown={e => handleKeyDown(e, () => updateOffset(offset + 1))}
                    aria-label="Go to next page"
                    tabIndex={0}
                />
                <Pagination.Last
                    onClick={() => updateOffset(pagesCount - 1)}
                    onKeyDown={e => handleKeyDown(e, () => updateOffset(pagesCount - 1))}
                    disabled={isLastPage}
                    aria-label="Go to last page"
                    tabIndex={0}
                />
            </Pagination>
        </nav>
    )
})

PaginationComponent.displayName = 'PaginationComponent'

export default PaginationComponent
