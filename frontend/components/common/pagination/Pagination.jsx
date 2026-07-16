'use client'

import React from 'react'
import { Pagination as BootstrapPagination } from 'react-bootstrap'

import { clampPageIndex } from '@/lib/pagination/page'

const WINDOW = 2

/** @param {number} pageCount @param {number} pageIndex @returns {(number|null)[]} */
const buildPageItems = (pageCount, pageIndex) => {
    const pages = new Set([
        0,
        pageCount - 1,
    ])
    for (let index = pageIndex - WINDOW; index <= pageIndex + WINDOW; index++) {
        if (index >= 0 && index < pageCount) pages.add(index)
    }

    const sorted = [...pages].sort((left, right) => left - right)
    /** @type {(number|null)[]} */
    const items = []
    let previous = null
    for (const index of sorted) {
        if (previous !== null && index - previous > 1) items.push(null)
        items.push(index)
        previous = index
    }
    return items
}

/**
 * @typedef {object} PaginationProps
 * @property {number} pageIndex
 * @property {number} pageCount
 * @property {(pageIndex: number) => void} onPageChange
 * @property {string} [ariaLabel]
 */

/** @param {PaginationProps} props */
const PaginationComponent = ({
    pageIndex,
    pageCount,
    onPageChange,
    ariaLabel = 'Pagination navigation',
}) => {
    if (pageCount <= 1) return null

    const currentPageIndex = clampPageIndex(pageIndex, pageCount)
    const isFirstPage = currentPageIndex === 0
    const isLastPage = currentPageIndex === pageCount - 1
    const pageItems = buildPageItems(pageCount, currentPageIndex)

    return (
        <nav
            aria-label={ariaLabel}
            className="d-flex align-items-center justify-content-center p-1">
            <BootstrapPagination className="mb-0">
                <BootstrapPagination.First
                    onClick={() => onPageChange(0)}
                    disabled={isFirstPage}
                    aria-label="Go to first page" />
                <BootstrapPagination.Prev
                    onClick={() => onPageChange(currentPageIndex - 1)}
                    disabled={isFirstPage}
                    aria-label="Go to previous page" />
                {pageItems.map((index, itemIndex) => (
                    index === null
                        ? <BootstrapPagination.Ellipsis
                            key={`ellipsis-${itemIndex}`}
                            disabled />
                        : <BootstrapPagination.Item
                            key={index}
                            active={index === currentPageIndex}
                            onClick={() => onPageChange(index)}
                            aria-label={`Go to page ${index + 1}`}
                            aria-current={index === currentPageIndex ? 'page' : undefined}>
                            {index + 1}
                        </BootstrapPagination.Item>
                ))}
                <BootstrapPagination.Next
                    onClick={() => onPageChange(currentPageIndex + 1)}
                    disabled={isLastPage}
                    aria-label="Go to next page" />
                <BootstrapPagination.Last
                    onClick={() => onPageChange(pageCount - 1)}
                    disabled={isLastPage}
                    aria-label="Go to last page" />
            </BootstrapPagination>
        </nav>
    )
}

const Pagination = React.memo(PaginationComponent)

Pagination.displayName = 'Pagination'

export default Pagination
