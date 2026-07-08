'use client'
import React from 'react'
import { Pagination } from 'react-bootstrap'

/** Max numbered page buttons rendered around the current page. */
const WINDOW = 2

/**
 * Builds the list of page indices to render, with `null` marking an ellipsis.
 * Always includes first, last, and a window around the current page.
 * @param {number} pagesCount
 * @param {number} offset current page (0-based)
 * @returns {Array<number|null>}
 */
const buildPageItems = (pagesCount, offset) => {
    const pages = new Set([
        0,
        pagesCount - 1,
    ])
    for (let k = offset - WINDOW; k <= offset + WINDOW; k++) {
        if (k >= 0 && k < pagesCount) {
            pages.add(k)
        }
    }

    const sorted = [
        ...pages,
    ].sort((a, b) => a - b)
    const items = [
    ]
    let prev = null
    for (const k of sorted) {
        if (prev !== null && k - prev > 1) {
            items.push(null) // ellipsis
        }
        items.push(k)
        prev = k
    }
    return items
}

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
    if (pagesCount <= 1) {
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
    const pageItems = buildPageItems(pagesCount, offset)

    return (
        <nav
            aria-label="Stream pagination navigation"
            className="d-flex align-items-center justify-content-center p-1"
        >
            <Pagination className="mb-0">
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
                {pageItems.map((k, index) => (
                    k === null
                        ? <Pagination.Ellipsis
                            key={`ellipsis-${index}`}
                            disabled
                        />
                        : <Pagination.Item
                            active={k === offset}
                            key={k}
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
