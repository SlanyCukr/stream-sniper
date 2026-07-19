import Pagination from './Pagination'

interface PaginatedResultsFooterProps {
    shown: number
    total: number
    pageIndex: number
    pageCount: number
    onPageChange: (pageIndex: number) => void
    ariaLabel?: string
}

const PaginatedResultsFooter = ({
    shown, total, pageIndex, pageCount, onPageChange, ariaLabel,
}: PaginatedResultsFooterProps) => (
    <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mt-3">
        <span className="mono small text-muted">Showing {shown} of {total}</span>
        <Pagination
            pageIndex={pageIndex}
            pageCount={pageCount}
            onPageChange={onPageChange}
            ariaLabel={ariaLabel}
        />
    </div>
)

export default PaginatedResultsFooter
