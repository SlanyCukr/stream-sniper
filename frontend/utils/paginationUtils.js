import { Pagination } from 'react-bootstrap'

/**
 * Renders pagination component with logic for showing page numbers
 * @param {number} currentPage - Current active page
 * @param {number} totalPages - Total number of pages
 * @param {function} setCurrentPage - Function to set current page
 * @param {number} maxPagesToShow - Maximum number of page buttons to show
 * @returns {JSX.Element} Pagination component
 */
export const renderPagination = (currentPage, totalPages, setCurrentPage, maxPagesToShow = 5) => {
    const items = [
    ]

    let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2))
    let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1)

    if (endPage - startPage + 1 < maxPagesToShow) {
        startPage = Math.max(1, endPage - maxPagesToShow + 1)
    }

    for (let page = startPage; page <= endPage; page++) {
        items.push(
            <Pagination.Item
                key={page}
                active={page === currentPage}
                onClick={() => setCurrentPage(page)}
            >
                {page}
            </Pagination.Item>,
        )
    }

    return (
        <Pagination>
            <Pagination.First
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1} />
            <Pagination.Prev
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1} />
            {items}
            <Pagination.Next
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === totalPages} />
            <Pagination.Last
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages} />
        </Pagination>
    )
}
