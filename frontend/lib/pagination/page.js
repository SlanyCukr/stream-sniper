/** @param {unknown} value */
const toNonNegativeInteger = value => (
    Number.isFinite(Number(value)) ? Math.max(0, Math.trunc(Number(value))) : 0
)

/** @param {unknown} value */
const toPositiveInteger = value => (
    Number.isFinite(Number(value)) ? Math.max(1, Math.trunc(Number(value))) : 1
)

/** @param {unknown} [pageIndex] @param {unknown} [pageSize] */
export const normalizePagination = (pageIndex = 0, pageSize = 20) => ({
    pageIndex: toNonNegativeInteger(pageIndex),
    pageSize: toPositiveInteger(pageSize),
})

/** @param {unknown} total @param {unknown} pageSize */
export const getPageCount = (total, pageSize) => {
    const safeTotal = toNonNegativeInteger(total)
    const safePageSize = toPositiveInteger(pageSize)
    return safeTotal === 0 ? 0 : Math.ceil(safeTotal / safePageSize)
}

/** @param {unknown} pageIndex @param {unknown} pageSize */
export const getRowOffset = (pageIndex, pageSize) => {
    const normalized = normalizePagination(pageIndex, pageSize)
    return normalized.pageIndex * normalized.pageSize
}

/** @param {unknown} pageIndex @param {unknown} pageCount */
export const clampPageIndex = (pageIndex, pageCount) => {
    const safePageIndex = toNonNegativeInteger(pageIndex)
    const safePageCount = toNonNegativeInteger(pageCount)
    return safePageCount === 0 ? 0 : Math.min(safePageIndex, safePageCount - 1)
}

/**
 * @template T
 * @param {T[]} items
 * @param {unknown} total
 * @param {unknown} pageIndex
 * @param {unknown} pageSize
 */
export const createPage = (items, total, pageIndex, pageSize) => {
    const normalized = normalizePagination(pageIndex, pageSize)
    const safeTotal = toNonNegativeInteger(total)
    return {
        items: Array.isArray(items) ? items : [],
        total: safeTotal,
        ...normalized,
        pageCount: getPageCount(safeTotal, normalized.pageSize),
    }
}
