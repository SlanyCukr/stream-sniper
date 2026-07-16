import Pagination from './Pagination'

/**
 * @param {{shown:number, total:number, pageIndex:number, pageCount:number, onPageChange:(pageIndex:number)=>void, ariaLabel?:string}} props
 */
const PaginatedResultsFooter = ({
    shown, total, pageIndex, pageCount, onPageChange, ariaLabel,
}) => (
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
